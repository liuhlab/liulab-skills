#!/usr/bin/env bash
# Layer 1 — static lint. No network, no model. Run on every change.
set -u
# `|| exit 1`, because every check below is relative to the repo root. A failed cd would
# otherwise leave the sweep running somewhere else, finding no secrets because it is
# looking at nothing, and reporting LINT PASS. A gate that cannot reach the tree it
# guards must fail, not pass.
cd "$(dirname "$0")/.." || exit 1
fail=0
err() { echo "FAIL: $*"; fail=1; }
ok()  { echo "  ok: $*"; }

echo "== manifests =="
for f in .claude-plugin/marketplace.json .claude-plugin/plugin.json; do
  if python3 -m json.tool "$f" >/dev/null 2>&1; then ok "$f is valid JSON"
  else err "$f is not valid JSON"; fi
done

plug=$(python3 -c 'import json; print(json.load(open(".claude-plugin/plugin.json"))["name"])' 2>/dev/null)
case "$plug" in
  lab) ok "plugin name is '$plug'" ;;
  *)   err "plugin name '$plug' must be lab" ;;
esac

echo "== skills =="
# 1536 is `skillListingMaxDescChars`: the platform's cap on ONE description in the skill
# listing. It is enforced per skill, below.
DESC_MAX=1536
total_desc=0
n_skills=0
for d in skills/*/; do
  s="${d}SKILL.md"
  name=$(basename "$d")
  [ -f "$s" ] || { err "$d has no SKILL.md"; continue; }
  fm_name=$(awk 'f && $1=="name:"{print $2; exit} /^---$/{f++}' "$s")
  if [ "$fm_name" = "$name" ]; then ok "$s frontmatter name matches dir"
  else err "$s frontmatter name '$fm_name' != dir '$name'"; fi
  # The naming policy is its own section, `== adopted skill names ==`, below.
  dlen=$(python3 - "$s" <<'EOF'
import sys
lines = open(sys.argv[1]).read().splitlines()
assert lines[0] == "---", "no frontmatter"
body, in_desc = [], False
for ln in lines[1:]:
    if ln == "---": break
    if ln.startswith("description:"):
        in_desc = True
        body.append(ln.split(":", 1)[1].strip().lstrip(">-").strip())
    elif in_desc and (ln.startswith("  ") or not ln.strip()):
        body.append(ln.strip())
    else:
        in_desc = False
print(len(" ".join(w for w in body if w)))
EOF
  ) || { err "$s frontmatter unparseable"; continue; }
  if [ "${dlen:-0}" -lt 20 ]; then err "$s description missing or too short"
  elif [ "$dlen" -gt "$DESC_MAX" ]; then
    err "$s description ${dlen} chars exceeds the ${DESC_MAX}-char per-skill listing cap"
  else ok "$s description present (${dlen}/${DESC_MAX} chars)"; fi
  total_desc=$((total_desc + dlen))
  n_skills=$((n_skills + 1))
done
# The sum is INFORMATION. It carried a FAIL until 2026-09, on the reading that 1536 was a
# budget the skills shared. It is not: it caps a single description, which is why the check
# above is per skill. The budget that really is shared is a fraction of the model's context
# window, and it spans every skill installed on the machine — other plugins, the user's own
# — not this plugin's. No number here can measure that, so nothing here may fail on it, and
# adding a skill must not fail the gate. Do not reinstate the sum.
ok "descriptions total ${total_desc} chars across ${n_skills} skills (informational)"

echo "== adopted skill names =="
# ADR 0013. A skill the lab wrote or derived is named `lab-*`. An adopted skill keeps its
# upstream name, and passes only when `upstream/` records it: in a merged upstream's pin
# (tracked) or in an attribution record (forked). `hq-mode` is the one derived skill without a
# `lab-*` name. The record formats are in upstream/README.md.
adopted_check() { # <root>: prints ok/FAIL lines, exits 1 on any FAIL
  python3 - "$1" <<'EOF'
import json
import os
import re
import sys

root = sys.argv[1]
oks, problems = [], []
HOW = ("a skill the lab wrote or derived is named lab-*; a skill taken from an upstream is "
       "recorded in upstream/: tracked, under `items` in upstream/<upstream>/pin.json; forked, "
       "as a record in upstream/attribution.json. Formats: upstream/README.md")
SHA = re.compile(r"^[0-9a-f]{40}$")
SKILL_PATH = re.compile(r"^skills/([^/]+)$")


def here(rel):
    return os.path.join(root, rel)


def load(rel):
    """The parsed JSON at `rel`, or None when it is absent or unreadable (reported)."""
    if not os.path.exists(here(rel)):
        return None
    try:
        with open(here(rel), encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        problems.append(f"{rel} is not valid JSON: {e}")
        return None


tracked = {}  # skill name -> the upstream whose pin maps it
upstreams = os.listdir(here("upstream")) if os.path.isdir(here("upstream")) else []
for u in sorted(d for d in upstreams if os.path.isdir(here(f"upstream/{d}"))):
    if not os.path.isfile(here(f"upstream/{u}/LICENSE")):
        problems.append(f"upstream/{u}/ has no LICENSE: an upstream's license travels with "
                        "what the lab takes from it, so copy it there verbatim")
    rel = f"upstream/{u}/pin.json"
    pin = load(rel)
    if pin is None:
        continue
    bad = []
    if not isinstance(pin, dict):
        pin, bad = {}, ["it is not a JSON object"]
    if not isinstance(pin.get("repo"), str):
        bad.append("`repo` is not a string")
    if not SHA.match(str(pin.get("commit", ""))):
        bad.append("`commit` is not a full 40-character commit")
    if pin.get("sync") not in ("merge", "review"):
        bad.append("`sync` is not `merge` or `review`")
    if not isinstance(pin.get("skills_dir"), str):
        bad.append("`skills_dir` is not a string")
    items = pin.get("items")
    if not isinstance(items, dict) or not all(isinstance(v, str) for v in items.values()):
        bad.append("`items` is not a map from upstream item to lab path")
        items = {}
    for b in bad:
        problems.append(f"{rel}: {b} (format: upstream/README.md)")
    if pin.get("sync") != "merge":
        # A reviewed upstream's items are all forked or taken as ideas, so its pin admits no
        # name. Each still maps to the lab file it feeds, and a map onto nothing is a dead
        # record the sync's summary would point the maintainer at.
        for item, path in sorted(items.items()):
            if not os.path.exists(here(path)):
                problems.append(f"{rel} maps `{item}` to `{path}`, which does not exist here: "
                                "map it to the lab file it feeds")
        continue
    for item, path in sorted(items.items()):
        m = SKILL_PATH.match(path)
        if not m or not os.path.isdir(here(path)):
            problems.append(f"{rel} maps `{item}` to `{path}`, which is not a skills/<name> "
                            "directory here: a tracked item is a whole skill")
            continue
        tracked[m.group(1)] = u
if tracked:
    oks.append(f"{len(tracked)} tracked skill(s) in the merged upstreams' pins")

forked = {}  # skill name -> the upstreams it was taken from
rel = "upstream/attribution.json"
records = load(rel)
if records is not None and not isinstance(records, dict):
    problems.append(f"{rel} is not a JSON object keyed by lab path (format: upstream/README.md)")
    records = None
for path, rec in sorted((records or {}).items()):
    sources = rec.get("from") if isinstance(rec, dict) else None
    if not isinstance(sources, list) or not sources:
        problems.append(f"{rel}: `{path}` has no `from` list naming where it came from")
        continue
    if not os.path.exists(here(path)):
        problems.append(f"{rel} records `{path}`, which does not exist here")
    names = []
    for src in sources:
        src = src if isinstance(src, dict) else {}
        u = str(src.get("upstream", ""))
        if not isinstance(src.get("item"), str) or not SHA.match(str(src.get("commit", ""))):
            problems.append(f"{rel}: a source of `{path}` lacks `item` or a full 40-character "
                            "`commit` (format: upstream/README.md)")
        if not u or not os.path.isfile(here(f"upstream/{u}/LICENSE")):
            problems.append(f"{rel}: `{path}` comes from `{u}`, and there is no "
                            f"upstream/{u}/LICENSE for its license to travel in")
        names.append(u)
    m = SKILL_PATH.match(path)
    if m:
        forked[m.group(1)] = ", ".join(names)
for name in sorted(set(tracked) & set(forked)):
    problems.append(f"skill '{name}' is both tracked and forked: forking moves it out of "
                    f"upstream/{tracked[name]}/pin.json's `items`, so delete it there")

skills_dir = here("skills")
for name in sorted(os.listdir(skills_dir)):
    if not os.path.isdir(os.path.join(skills_dir, name)):
        continue
    if name.startswith("lab-"):
        oks.append(f"skill '{name}' is lab-written or derived (lab-*)")
    elif name == "hq-mode":
        oks.append(f"skill '{name}' is the mode, the one derived skill without a lab-* name")
    elif name in tracked:
        oks.append(f"skill '{name}' is tracked from {tracked[name]} "
                   f"(upstream/{tracked[name]}/pin.json)")
    elif name in forked:
        oks.append(f"skill '{name}' is forked from {forked[name]} (upstream/attribution.json)")
    else:
        problems.append(f"skill '{name}' is not lab-* and is recorded nowhere as adopted: {HOW}")


# Upstream text passes vale and markdownlint through configuration, never by editing it: one
# `.vale.ini` section and one markdownlint override, each listing the adopted skills by name.
def read(rel):
    try:
        with open(here(rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


VALE = ".vale.ini's adopted-skill section [skills/{...}/*.md]"
MDL = ".markdownlint-cli2.yaml's adopted-skill override (a `- \"skills/<name>/**\"` filter line)"
heads = re.findall(r"^\[skills/\{([^}]*)\}/\*\.md\][ \t]*$", read(".vale.ini"), re.M)
if len(heads) > 1:
    problems.append(f".vale.ini has {len(heads)} adopted-skill sections; keep one")
vale = {n.strip() for h in heads for n in h.split(",") if n.strip()}
mdl = set(re.findall(r'^[ \t]*-[ \t]*"skills/([^/"*{}]+)/\*\*"[ \t]*$',
                     read(".markdownlint-cli2.yaml"), re.M))
for name in sorted(tracked):
    for listed, where in ((vale, VALE), (mdl, MDL)):
        if name not in listed:
            problems.append(f"tracked skill '{name}' is missing from {where}: upstream text "
                            "passes the gate through configuration, never by editing it")
for name in sorted((vale ^ mdl) - set(tracked)):
    have, lack = (".vale.ini's adopted-skill section", ".markdownlint-cli2.yaml") \
        if name in vale else (".markdownlint-cli2.yaml's adopted-skill override", ".vale.ini")
    problems.append(f"'{name}' is in {have} but not in {lack}: the two lists must agree")
for name in sorted((vale | mdl) - set(tracked) - set(forked)):
    problems.append(f"the gate exempts '{name}', which is not recorded as adopted: the "
                    "exemption is for upstream text, and lab text meets the gate")
if vale and vale == mdl:
    oks.append(f"vale and markdownlint exempt the same {len(vale)} adopted skill(s)")

for line in oks:
    print(f"  ok: {line}")
for line in problems:
    print(f"FAIL: {line}")
sys.exit(1 if problems else 0)
EOF
}

# Self-tests first, on fixture trees built here and deleted on the way out, in both
# directions: a check that can no longer fail looks exactly like one that passes.
an_fx=$(mktemp -d "${TMPDIR:-/tmp}/lab-adopted.XXXXXX")
trap 'rm -rf "$an_fx"' EXIT
adopted_case() { # <label> <root> <expected-exit> <substring the output must hold>
  local label="$1" root="$2" wantrc="$3" want="$4" out rc
  out=$(adopted_check "$root" 2>&1)
  rc=$?
  if [ "$rc" -eq "$wantrc" ] && printf '%s\n' "$out" | grep -qF -- "$want"; then
    ok "naming self-test: $label"
  else
    err "naming self-test: $label — wanted exit $wantrc and '$want', got exit $rc: $out"
  fi
}
an_tree() { # <fixture> <skill>...: a fixture repo holding lab-x and the named skill dirs
  local root="$an_fx/$1"; shift
  mkdir -p "$root/skills/lab-x"
  for s in "$@"; do mkdir -p "$root/skills/$s"; done
  printf '%s' "$root"
}

adopted_case "an unrecorded name fails and says how to record it" "$(an_tree unrecorded foo)" 1 \
  "skill 'foo' is not lab-* and is recorded nowhere as adopted"
adopted_case "the failure points at the formats" "$an_fx/unrecorded" 1 "upstream/README.md"
adopted_case "hq-mode passes unrecorded" "$(an_tree mode hq-mode)" 0 "skill 'hq-mode' is the mode"

an_pin() { # <root> <upstream> <merge|review> <item>: a pin mapping one item to skills/<item>
  mkdir -p "$1/upstream/$2"
  printf 'MIT License\n' >"$1/upstream/$2/LICENSE"
  printf '{"repo": "https://example.org/%s", "commit": "%s", "sync": "%s", "skills_dir": "skills", "items": {"%s": "skills/%s"}}\n' \
    "$2" "0123456789abcdef0123456789abcdef01234567" "$3" "$4" "$4" >"$1/upstream/$2/pin.json"
}
an_lists() { # <root> <vale names, comma-separated> <markdownlint names...>: the two exemptions
  local root="$1" vale="$2"; shift 2
  printf '[skills/{%s}/*.md]\nBasedOnStyles = Lab\n' "$vale" >"$root/.vale.ini"
  { printf 'overrides:\n  - filter:\n'
    for s in "$@"; do printf '      - "skills/%s/**"\n' "$s"; done
    printf '    combine: merge\n    config:\n      MD041: false\n'; } >"$root/.markdownlint-cli2.yaml"
}
an_root=$(an_tree tracked foo); an_pin "$an_root" up merge foo; an_lists "$an_root" foo foo
adopted_case "a name a merged upstream's pin maps passes as tracked" "$an_fx/tracked" 0 \
  "skill 'foo' is tracked from up"
an_pin "$(an_tree reviewed foo)" up review foo
adopted_case "a reviewed upstream's pin admits no name" "$an_fx/reviewed" 1 \
  "skill 'foo' is not lab-* and is recorded nowhere as adopted"
an_pin "$(an_tree dangling)" up review gone
adopted_case "a reviewed upstream's pin mapping onto nothing fails" "$an_fx/dangling" 1 \
  "maps \`gone\` to \`skills/gone\`, which does not exist here"

an_record() { # <root> <upstream> <item>: an attribution record forking skills/<item>
  printf '{"skills/%s": {"from": [{"upstream": "%s", "item": "%s", "commit": "%s"}], "changes": "fixture"}}\n' \
    "$3" "$2" "$3" "0123456789abcdef0123456789abcdef01234567" >"$1/upstream/attribution.json"
}
an_root=$(an_tree forked bar); mkdir -p "$an_root/upstream/up"; printf 'MIT License\n' >"$an_root/upstream/up/LICENSE"
an_record "$an_root" up bar
adopted_case "a name an attribution record lists passes as forked" "$an_root" 0 \
  "skill 'bar' is forked from up"
an_root=$(an_tree unlicensed bar); mkdir -p "$an_root/upstream"
an_record "$an_root" nowhere bar
adopted_case "a record whose upstream has no license fails" "$an_root" 1 \
  "no upstream/nowhere/LICENSE"
an_root=$(an_tree both foo); an_pin "$an_root" up merge foo; an_record "$an_root" up foo
adopted_case "a skill both tracked and forked fails" "$an_root" 1 "both tracked and forked"

# The gate passes upstream text through two lists of names, one in `.vale.ini` and one in
# `.markdownlint-cli2.yaml`. Two lists that must agree drift unless something checks them.
an_root=$(an_tree unlisted foo); an_pin "$an_root" up merge foo
adopted_case "a tracked skill missing from the vale section fails" "$an_root" 1 \
  "tracked skill 'foo' is missing from .vale.ini"
an_root=$(an_tree halflisted bar); mkdir -p "$an_root/upstream/up"
printf 'MIT License\n' >"$an_root/upstream/up/LICENSE"; an_record "$an_root" up bar; an_lists "$an_root" bar
adopted_case "a vale name the markdownlint override misses fails" "$an_root" 1 \
  "'bar' is in .vale.ini's adopted-skill section but not in .markdownlint-cli2.yaml"
an_root=$(an_tree overlisted foo); an_pin "$an_root" up merge foo; an_lists "$an_root" foo,lab-x foo lab-x
adopted_case "an exemption for a skill nobody adopted fails" "$an_root" 1 \
  "exempts 'lab-x', which is not recorded as adopted"

rm -rf "$an_fx"
trap - EXIT

# Then this tree. stderr is captured too, so a crash in the check is a FAIL, never a pass.
an_out=$(adopted_check . 2>&1)
an_rc=$?
printf '%s\n' "$an_out"
if [ "$an_rc" -ne 0 ]; then fail=1
elif [ -z "$an_out" ]; then err "the naming check printed nothing, so it checked nothing"; fi

echo "== no-secrets sweep =="
# Publishable tree only (what git tracks + working copies), minus this test
# and the gitignored build and cache trees. Nothing excluded here is publishable
# — every entry is in .gitignore, and this list is kept in step with it.
# `.pixi/` holds vendored conda packages carrying both IP literals and key
# material, and `.ruff_cache/` stores absolute paths (so, the local username):
# sweeping either would turn this gate permanently red the day someone runs
# `pixi run check`, which is the fastest way to get the gate disabled.
# `--exclude=.git` is NOT redundant with `--exclude-dir=.git`: in a linked git
# worktree `.git` is a FILE holding `gitdir: <absolute path>`, which contains the
# local username — so without it this gate flags its own plumbing and reports a
# leak that is not there. A false positive here is how a security gate gets
# switched off, so both spellings stay.
#
# `.claude/` holds both kinds: machine-local files, all in .gitignore
# (`settings.local.json`, `worktrees/`, the installer's `skills/`), and the
# tracked maintainer-only skill in `.claude/commands/`. No directory exclusion
# splits the two, so the walk skips `.claude/` and git names what in it is
# publishable — tracked, or new and not ignored — to be swept file by file.
claude_files=()
while IFS= read -r f; do claude_files+=("./$f"); done \
  < <(git ls-files -co --exclude-standard -- .claude 2>/dev/null)
SWEEP() {
  local hit=1
  grep -rnE "$1" \
    --exclude-dir=.git --exclude=.git --exclude-dir=.claude --exclude-dir=.pixi \
    --exclude-dir=site --exclude-dir=dist --exclude-dir=build \
    --exclude-dir=.cache --exclude-dir=__pycache__ \
    --exclude-dir=.ruff_cache --exclude-dir=.mypy_cache \
    --exclude-dir=.pytest_cache \
    --exclude=lint.sh . && hit=0
  if [ "${#claude_files[@]}" -gt 0 ] && grep -nE "$1" /dev/null "${claude_files[@]}"; then hit=0; fi
  return "$hit"
}
ok "the sweep reads the ${#claude_files[@]} publishable file(s) under .claude/ by name"
# 0.0.0.0 / 127.0.0.1 are well-known non-secret addresses (used in the
# "bind to localhost only" safety instructions) — everything else flags.
#
# A four-part version number is indistinguishable from an IPv4 address by regex, and
# `pixi.lock` is full of them: `pandas-stubs>=1.1.0.11`, `typing-extensions>=3.10.0.0`.
# So one more exemption, kept as narrow as it can be — the number has to sit immediately
# after a comparison operator, which is a version specifier and nothing else. A real
# address in a URL (`http://10.0.0.1/simple`) has no operator in front of it and still
# flags, which is the case this rule exists for.
VERSION_SPEC='(>=|<=|==|~=|!=|<|>)[0-9]+(\.[0-9]+){3}'
if SWEEP '([0-9]{1,3}\.){3}[0-9]{1,3}' | grep -vE '0\.0\.0\.0|127\.0\.0\.1' | grep -vE "$VERSION_SPEC"; then
  err "IPv4-looking literal found (above)"
else ok "no IP literals (0.0.0.0/127.0.0.1 exempt)"; fi
if SWEEP 'Identity[F]ile|BEGIN [A-Z ]*PRIVATE[ ]KEY|ssh-(rsa|ed25519)[ ]AAAA'; then
  err "key material / IdentityFile reference found (above)"
else ok "no key material"; fi
# The Edison platform API key. Only the shipped placeholder may stand on the
# right of an assignment. Both spellings are swept: `EDISON_PLATFORM_API_KEY` is
# the name `edison-client` actually reads, and `EDISON_KEY` is the near miss a
# user who set it up from memory would write — a real key committed under the
# wrong name is exactly as leaked as one committed under the right name.
# The preflight is invoked as a FILE with a bare interpreter, not through `edison-cli`:
# this is a security control, and it must keep working on a tree where nothing is
# installed. That is why `src/edison_cli/preflight.py` imports only the standard library.
if SWEEP '(EDISON_PLATFORM_API_KEY|EDISON_KEY)[[:space:]]*=' | grep -vF "$(python3 src/edison_cli/preflight.py --constants | sed -n 's/^PLACEHOLDER=//p' | grep . || echo NO-PLACEHOLDER-FROM-THE-PREFLIGHT)"; then
  err "Edison API key assigned to something other than the placeholder (above)"
else ok "no Edison API key (only the PASTE-YOUR-... placeholder)"; fi
# Usernames come from THIS machine's ssh config at test time — none are
# stored in the repo, but none may appear in it either. Shared CI service
# accounts are exempt for the same reason the hostname sweep below exempts
# the public forges: every GitHub-hosted machine runs as the same well-known
# name, which is nobody's identity and is also an ordinary English word this
# repo's own prose (and the copied scripts/check.sh) uses. It can never be a
# lab username, so exempting it costs the sweep nothing.
users=$( (awk 'tolower($1)=="user"{print $2}' ~/.ssh/config 2>/dev/null; whoami) \
         | grep -vxE 'runner' | sort -u)
uleak=0
for u in $users; do
  if SWEEP "(^|[^a-zA-Z0-9_-])$u([^a-zA-Z0-9_-]|\$)"; then
    err "local username '$u' appears in the repo (above)"
    uleak=1
  fi
done
# Guarded, because an unconditional success line printed `ok: no usernames leaked`
# directly beneath `FAIL: username appears in the repo`. A gate that contradicts
# itself in the same breath teaches the reader to skim past both.
if [ "$uleak" -eq 0 ]; then
  ok "no local ssh-config usernames leaked (checked $(printf '%s\n' "$users" | grep -c .) names)"
fi
# Hostnames likewise come from THIS machine's ssh config at test time — the
# repo may reference hosts only by alias. Only dotted values are swept
# (single-label names are indistinguishable from alias vocabulary); wildcards
# and public forges are skipped; IP-valued HostNames also trip the IP sweep.
hosts=$(awk 'tolower($1)=="hostname"{print $2}' ~/.ssh/config 2>/dev/null \
        | grep '\.' | grep -v '[*?%]' \
        | grep -viE '^(localhost|127\.0\.0\.1|github\.com|gitlab\.com|bitbucket\.org)$' \
        | sort -u)
hcount=0
hleak=0
for h in $hosts; do
  hcount=$((hcount + 1))
  hre=$(printf '%s' "$h" | sed 's/[][\.^$*+?(){}|]/\\&/g')
  if SWEEP "(^|[^a-zA-Z0-9._-])$hre([^a-zA-Z0-9._-]|\$)"; then
    err "local ssh-config hostname '$h' appears in the repo (above)"
    hleak=1
  fi
done
if [ "$hleak" -eq 0 ]; then
  ok "no local ssh-config hostnames leaked (checked $hcount names)"
fi

echo "== vendor attribution =="
# The Edison platform is run by Edison Scientific, FutureHouse's commercial spinout, and the
# Edison entry in GLOSSARY.md is the single authority on that. Four other registers say it in
# their own words — the skill body, its trigger description, README.md and the published page
# — and nothing can lint five registers for "says the right thing". This lints all of them
# for "never says the wrong thing". Same shape as the eval suite's DENY assertions, which
# guard one specific wrong job value the same way.
#
# Three appearances of the old name are CORRECT and must survive:
#   * the platform's job-name strings, `job-futurehouse-...`;
#   * the persona picker's handle, `@FutureHouse/...`;
#   * CHANGELOG.md, whose entries record what shipped and are not rewritten afterwards.
# The first two are naming residue of the spinout and are live API values — eliding them here
# is what stops this rule being "fixed" by editing a string the client has to send verbatim.
#
# Narrow on purpose: a regression test for one known error, not a factual-claims checker. It
# matches the shapes that put FutureHouse in charge of the platform and nothing else, so
# "Edison Scientific, FutureHouse's commercial spinout" passes and must keep passing.
VENDOR_WRONG='future[ -]?house[^[:space:]]{0,2}[[:space:]]+'
VENDOR_WRONG="$VENDOR_WRONG"'(edison|research|platform|product|service|api|client'
VENDOR_WRONG="$VENDOR_WRONG"'|runs?|operates?|owns?|hosts?|provides?)'
VENDOR_WRONG="$VENDOR_WRONG"'|(run|built|operated|owned|made|developed|provided|hosted|created)'
VENDOR_WRONG="$VENDOR_WRONG"'[[:space:]]+by[[:space:]]+future[ -]?house'
vendor_elide() { sed -e 's/job-futurehouse-[A-Za-z0-9._-]*//g' -e 's|@FutureHouse/[A-Za-z0-9._-]*||g'; }

# Both directions, every run. A sweep that can no longer fire looks exactly like a sweep that
# passes, and this one guards prose that nothing else re-checks.
vendor_probe() { # <label> <trips|clears> <text>
  local label="$1" want="$2" text="$3" got
  if printf '%s\n' "$text" | vendor_elide | grep -qiE "$VENDOR_WRONG"; then got=trips; else got=clears; fi
  if [ "$got" = "$want" ]; then ok "vendor probe: $label $want the check"
  else err "vendor probe: $label — wanted '$want', got '$got': $text"; fi
}
vendor_probe "the possessive re-attribution" trips  "FutureHouse's Edison research platform, reached from a lab machine"
vendor_probe "the bare adjective form"       trips  "the FutureHouse Edison platform"
vendor_probe "the run-by form"               trips  "the Edison platform, run by FutureHouse"
vendor_probe "the corrected attribution"     clears "run by Edison Scientific — FutureHouse's commercial spinout"
vendor_probe "a job-name string"             clears "get_session returns job-futurehouse-data-analysis-aries"
vendor_probe "the persona picker handle"     clears "the picker offers @FutureHouse/data-analysis-aries"

# CHANGELOG.md is excluded by name rather than by pattern: its older entries carry the wrong
# attribution as shipped history, and rewriting a release note to satisfy a linter hides the
# error instead of correcting it.
vendor_hits=$(SWEEP '[Ff]uture[ -]?[Hh]ouse' | grep -v '^\./CHANGELOG\.md:' \
              | vendor_elide | grep -iE "$VENDOR_WRONG")
if [ -n "$vendor_hits" ]; then
  printf '%s\n' "$vendor_hits"
  err "the Edison platform is attributed to FutureHouse (above, with job names elided) — Edison Scientific runs it; GLOSSARY.md's Edison entry is the authority"
else
  ok "no FutureHouse attribution of the Edison platform (CHANGELOG history exempt)"
fi

echo "== check-hpc-config.sh self-test =="
# Each case gets its own empty HOME: the script refuses outright while the
# pre-rename ~/.claude/compute exists, and a maintainer's own machine may
# still have one — which would turn the first case into a vacuous pass.
hpc_home=$(mktemp -d)
out=$(HOME="$hpc_home" bash skills/lab-hpc/scripts/check-hpc-config.sh -F /dev/null)
rc=$?
if [ $rc -eq 1 ] && [ "$(printf '%s\n' "$out" | grep -c 'NOT CONFIGURED')" -eq 2 ] \
   && ! printf '%s' "$out" | grep -v 'NOT CONFIGURED' | grep -q CONFIGURED; then
  ok "empty ssh config → both clusters NOT CONFIGURED, exit 1"
else
  err "check-hpc-config.sh with empty config: expected NOT CONFIGURED + exit 1, got exit $rc: $out"
fi
mkdir -p "$hpc_home/.claude/compute"
out=$(HOME="$hpc_home" bash skills/lab-hpc/scripts/check-hpc-config.sh -F /dev/null)
rc=$?
if [ $rc -eq 1 ] && printf '%s' "$out" | grep -q 'OLD LOCATION' \
   && printf '%s' "$out" | grep -qxF '  fix: mv ~/.claude/compute ~/.claude/lab'; then
  ok "pre-rename ~/.claude/compute → OLD LOCATION + the mv, exit 1"
else
  err "check-hpc-config.sh with ~/.claude/compute: expected OLD LOCATION + mv + exit 1, got exit $rc: $out"
fi
mkdir -p "$hpc_home/.claude/lab"
out=$(HOME="$hpc_home" bash skills/lab-hpc/scripts/check-hpc-config.sh -F /dev/null)
rc=$?
if [ $rc -eq 1 ] && printf '%s' "$out" | grep -q 'both exist' && ! printf '%s' "$out" | grep -q 'mv '; then
  ok "both config dirs → OLD LOCATION, no mv over an existing directory, exit 1"
else
  err "check-hpc-config.sh with both dirs: expected 'both exist' and no mv, got exit $rc: $out"
fi
rm -rf "$hpc_home"

echo "== edison preflight self-test =="
# Fixtures are built here and deleted on the way out; none is ever committed.
# A committed fixture holding a fake key would trip the Edison rule in the sweep
# above — which is the rule working, not a false positive, so the fixtures live
# outside the tree the sweep reads.
# Every case passes `-f`, which also suppresses the environment variable: on a
# maintainer's machine the real key IS exported, and without that suppression
# every fixture would report configured and prove nothing.
# A path and a bare interpreter, for the same reason as the sweep above.
edison_pf=src/edison_cli/preflight.py
fx=$(mktemp -d "${TMPDIR:-/tmp}/lab-edison-fixtures.XXXXXX")
trap 'rm -rf "$fx"' EXIT

# The preflight owns the constants describing the key file, so the fixtures are built from
# what it prints rather than from literals of their own. A placeholder fixture that restated
# the string would go on passing after the preflight's placeholder moved, which is the drift
# the section below exists to catch.
edison_consts=$(python3 "$edison_pf" --constants)
edison_const() { printf '%s\n' "$edison_consts" | sed -n "s/^$1=//p"; }
ed_var=$(edison_const VAR)
ed_placeholder=$(edison_const PLACEHOLDER)
ed_keyfile=$(edison_const KEYFILE)
ed_mode_glob=$(edison_const MODE_GLOB)
ed_mode_label=$(edison_const MODE_LABEL)
ed_chmod=$(edison_const CHMOD_MODE)

edison_case() { # <label> <key-file> <expected-verdict-substring> <expected-exit>
  local label="$1" file="$2" want="$3" wantrc="$4" out rc
  out=$(python3 "$edison_pf" -f "$file")
  rc=$?
  if [ "$rc" -eq "$wantrc" ] && printf '%s\n' "$out" | grep -qF "$want"; then
    ok "edison preflight: $label"
  else
    err "edison preflight: $label — wanted '$want' and exit $wantrc, got exit $rc: $out"
  fi
}

printf 'export %s=%s\n' "$ed_var" "$ed_placeholder" >"$fx/placeholder.env"
chmod "$ed_chmod" "$fx/placeholder.env"
# Not a key: 22 characters of the word "fixture", at a mode the preflight must reject.
printf 'export %s=fixture-not-a-real-key\n' "$ed_var" >"$fx/open-perms.env"
chmod 644 "$fx/open-perms.env"
# The path that lets work PROCEED, which nothing covered until 2026-09: a replaced value at
# an owner-only mode. Mode 400 on purpose — it is owner-only without being 600, so this case
# fails the moment someone narrows the rule back to the one mode the remedy hands out.
printf 'export %s=fixture-stands-in-for-a-replaced-key\n' "$ed_var" >"$fx/replaced.env"
chmod 400 "$fx/replaced.env"
: >"$fx/empty.env"
chmod "$ed_chmod" "$fx/empty.env"
# Present, correctly permissioned, and assigning nothing — what a user who edited the file
# and deleted the wrong line leaves behind.
printf '# no assignment here\n' >"$fx/no-assignment.env"
chmod "$ed_chmod" "$fx/no-assignment.env"

edison_case "missing file"       "$fx/absent.env"      "key file: MISSING"                 1
edison_case "placeholder unreplaced" "$fx/placeholder.env" "key: PLACEHOLDER"              1
edison_case "over-permissive mode"   "$fx/open-perms.env"  "key file: PERMISSIONS TOO OPEN" 1
edison_case "empty key file"         "$fx/empty.env"       "key file: EMPTY"               1
edison_case "file assigns no key"    "$fx/no-assignment.env" "key: NOT SET"                1
edison_case "replaced key, owner-only" "$fx/replaced.env"  "edison: CONFIGURED"            0

rm -rf "$fx"
trap - EXIT

echo "== edison key-file constants =="
# One owner for the four constants describing the key file — the variable name the client
# reads, the shipped placeholder, the file's location, and which modes are acceptable — and
# it is the preflight above. Everything else in the tree has to AGREE with what it prints
# rather than restate it. The failure this catches is specific: let the onboarding
# template's placeholder drift from the preflight's, and a user who never replaced it is
# told CONFIGURED and then fails minutes later at authentication — the exact failure the
# placeholder check exists to prevent.
if [ -z "$edison_consts" ]; then
  err "$edison_pf --constants printed nothing, so nothing could be cross-checked"
else
  cmissing=""
  for k in VAR PLACEHOLDER KEYFILE MODE_GLOB MODE_LABEL CHMOD_MODE; do
    printf '%s\n' "$edison_consts" | grep -q "^$k=." || cmissing="$cmissing $k"
  done
  if [ -n "$cmissing" ]; then err "--constants printed no value for:$cmissing"
  else ok "--constants prints every key-file constant"; fi
  # The shape is the contract: one KEY=value per line and nothing else, so a shell or a
  # python check can parse it. A stray sentence here would also be the first place a future
  # edit could print something that is not a constant.
  if printf '%s\n' "$edison_consts" | grep -qvE '^[A-Z_]+=.'; then
    printf '%s\n' "$edison_consts" | grep -vE '^[A-Z_]+=.'
    err "--constants printed a line that is not KEY=value (above)"
  else ok "--constants prints KEY=value lines only"; fi

  const_case() { # <label> <file> <literal-that-must-appear>
    local label="$1" file="$2" want="$3"
    if [ ! -f "$file" ]; then err "$label — $file is missing"
    elif grep -qF -- "$want" "$file"; then ok "$label"
    else err "$label — '$want' appears nowhere in $file"; fi
  }

  tmpl=templates/edison.env
  page=docs/skills/lab-edison.md
  const_case "$tmpl assigns the owned variable and placeholder" "$tmpl" \
    "export $ed_var=$ed_placeholder"
  const_case "$tmpl names the owned location"   "$tmpl" "$ed_keyfile"
  const_case "$tmpl hands out the owned chmod"  "$tmpl" "chmod $ed_chmod"
  const_case "$page names the owned variable"    "$page" "$ed_var"
  const_case "$page prints the owned placeholder" "$page" "$ed_placeholder"
  const_case "$page names the owned location"    "$page" "$ed_keyfile"
  const_case "$page hands out the owned chmod"   "$page" "chmod $ed_chmod"

  # The remedy every document repeats has to be a mode the preflight actually accepts.
  # Unquoted so the glob globs; shellcheck reads that as word splitting.
  # shellcheck disable=SC2254
  case "$ed_chmod" in
    $ed_mode_glob) ok "chmod $ed_chmod satisfies the $ed_mode_label rule ($ed_mode_glob)" ;;
    *) err "the remedy hands out chmod $ed_chmod, which the preflight's own $ed_mode_glob test rejects" ;;
  esac

  # The sweep's Edison exemption, two ways. First: it must not restate the placeholder
  # anywhere in this file — a second copy is a second thing to forget.
  if grep -qF -- "$ed_placeholder" tests/lint.sh; then
    err "tests/lint.sh restates the placeholder; it must read it from $edison_pf"
  else
    ok "the no-secrets sweep reads the placeholder from the preflight"
  fi
  # Second, and behavioural: the template's assignment is the one line in the tree that may
  # hold the placeholder, so the sweep's own regex over it, minus what the preflight prints,
  # must come out empty. This is what fails when the template's placeholder drifts.
  if grep -E "($ed_var|EDISON_KEY)[[:space:]]*=" "$tmpl" | grep -vF "$ed_placeholder"; then
    err "$tmpl assigns something the preflight's placeholder does not exempt (above)"
  else
    ok "$tmpl's assignment is exactly what the sweep exempts"
  fi
fi

echo "== edison provenance =="
# Every Edison reference page opens with a provenance block: the page's default source, the
# date it was checked, and the tier that holds unless a claim says otherwise — verified, read
# or unverified. See `docs/adr/0009-facts-carry-their-provenance.md`.
#
# Vendor facts are not cluster facts. The vendor moves them without telling anyone, and
# several of them can only be observed by spending a credit, so a page has to say how it
# knows. Three wrong claims shipped in four releases before this check existed, each caught by
# a person rather than by anything here.
#
# What this checks is that the block is THERE and PARSES: a real calendar date and one of the
# three tier words. It cannot check that a date is honest — nothing can — and it must not read
# as though it did: whether the package still says what the page says is answered only by
# re-reading the package.
prov_n=0
for f in skills/lab-edison/references/*.md; do
  [ -f "$f" ] || continue
  prov_n=$((prov_n + 1))
  # stderr is captured too, so a crash in here is a FAIL and never a silent pass.
  msg=$(python3 - "$f" 2>&1 <<'EOF'
import datetime
import pathlib
import re
import sys

BLOCK = re.compile(
    r"^> \*\*Provenance\*\* — Source: (?P<source>.+?) · Checked: (?P<date>[^ ·]+) ·"
    r" Default tier: (?P<tier>[A-Za-z]+)"
)
TIERS = ("verified", "read", "unverified")

head = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()[:6]
found = [m for m in (BLOCK.match(line) for line in head) if m]
if not found:
    print("no provenance block in the first 6 lines")
elif not found[0]["source"].strip():
    print("the Source field is empty")
elif found[0]["tier"] not in TIERS:
    print(f"default tier '{found[0]['tier']}' is not one of {', '.join(TIERS)}")
else:
    try:
        datetime.date.fromisoformat(found[0]["date"])
    except ValueError:
        print(f"Checked date '{found[0]['date']}' is not a real YYYY-MM-DD date")
EOF
  )
  if [ -n "$msg" ]; then err "$f: $msg"
  else ok "$f carries a provenance block that parses"; fi
done
if [ "$prov_n" -eq 0 ]; then
  err "no pages under skills/lab-edison/references/, so the provenance rule checked nothing"
fi

# ======================= Codex and Kimi Code =======================
# Two rules for the agents beside Claude Code, from #91. Both go through one checker,
# `agent_check <rule> <skills-dir> [triggers] [forked]`, which prints a `FAIL<TAB>` or `ok<TAB>` line per
# finding. Probes run each rule on fixture trees first, both ways, because a check that can no
# longer fire looks exactly like one that passes. Standard library only, like the rest of this
# file, so `bash tests/lint.sh` runs outside pixi.
agent_check() {
  python3 - "$1" "$2" "${3:-}" "${4:-}" <<'EOF'
import pathlib
import re
import sys

rule, root, table = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
forked = {n.strip() for n in sys.argv[4].split(",") if n.strip()}
skills = {p.parent.name: p for p in sorted(root.glob("*/SKILL.md"))}


def frontmatter(path):
    keys, key = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        if ln == "---":
            break
        m = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", ln)
        if m:
            key = m[1]
            keys[key] = [m[2].strip()]
        elif key and (ln.startswith(" ") or not ln.strip()):
            keys[key].append(ln.strip())
    out = {}
    for k, parts in keys.items():
        v = re.sub(r"^[>|][+-]?\s*", "", " ".join(p for p in parts if p))
        if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


def held_back_in_codex(path):
    """True when agents/openai.yaml sets policy.allow_implicit_invocation: false."""
    if not path.is_file():
        return False
    in_policy = False
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if not ln[0].isspace():
            in_policy = ln.split("#")[0].strip() == "policy:"
        elif in_policy and re.fullmatch(r"\s+allow_implicit_invocation:\s*false\s*(#.*)?", ln):
            return True
    return False


def units(s):
    return len(s.encode("utf-16-le")) // 2


def kimi_sees(desc, listing_max=250, ellipsis=3):
    """Kimi Code lists a description over 250 UTF-16 units as its first 247 plus '...'."""
    if units(desc) <= listing_max:
        return desc
    seen = ""
    for ch in desc:
        if units(seen + ch) > listing_max - ellipsis:
            break
        seen += ch
    return seen


if rule == "invocation":
    for name, skill in skills.items():
        keyed = frontmatter(skill).get("disable-model-invocation", "").lower() == "true"
        filed = held_back_in_codex(skill.parent / "agents" / "openai.yaml")
        if keyed and not filed:
            print(f"FAIL\t{name} sets disable-model-invocation: true, but no agents/openai.yaml"
                  " sets policy.allow_implicit_invocation: false, so Codex can invoke it"
                  " unasked. Copy the shape of skills/lab-edison/agents/openai.yaml")
        elif filed and not keyed:
            print(f"FAIL\t{name}: agents/openai.yaml holds it back in Codex, but without"
                  " disable-model-invocation: true Claude Code and Kimi Code still invoke it."
                  " Set both or neither")
        elif keyed:
            print(f"ok\t{name} is user-invoked in Claude Code, Kimi Code and Codex")

if rule == "frontload":
    triggers = {}
    for ln in table.splitlines():
        if ln.strip():
            name, _, words = ln.partition(":")
            triggers[name.strip()] = [w.strip() for w in words.split(",") if w.strip()]
    for name in sorted(set(triggers) - set(skills)):
        print(f"FAIL\ttriggers are recorded for {name}, which is not a skill. Drop its row")
    for name, skill in skills.items():
        if name not in triggers:
            if name.startswith("lab-") or name == "hq-mode" or name in forked:
                print(f"FAIL\t{name} is lab-owned and has no triggers recorded. Add a row"
                      " naming the words a request uses when it wants this skill")
            continue
        seen = kimi_sees(frontmatter(skill).get("description", ""))
        # From a word start, so `arc` is not found inside `search` but `node` finds `nodes`.
        late = [w for w in triggers[name]
                if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(w), seen, re.IGNORECASE)]
        if late:
            print(f"FAIL\t{name}: Kimi Code's listing ends at '...{seen[-40:]}', so it never"
                  f" sees: {', '.join(late)}. Move them forward")
        else:
            print(f"ok\t{name}: Kimi Code's listing keeps all {len(triggers[name])} triggers")
EOF
}
agent_report() { # <checker output>
  while IFS="$(printf '\t')" read -r verdict msg; do
    case "$verdict" in
      ok)   ok "$msg" ;;
      FAIL) err "$msg" ;;
    esac
  done <<EOF
$1
EOF
}
ag=$(mktemp -d "${TMPDIR:-/tmp}/lab-agent-fixtures.XXXXXX")
trap 'rm -rf "$ag"' EXIT
fx_skill() { # <case> <name> <description> [extra frontmatter line]
  mkdir -p "$ag/$1/$2"
  { printf -- '---\nname: %s\ndescription: %s\n' "$2" "$3"
    [ -z "${4:-}" ] || printf '%s\n' "$4"
    printf -- '---\n\n# %s\n' "$2"; } >"$ag/$1/$2/SKILL.md"
}
fx_openai() { # <case> <name> <file body>
  mkdir -p "$ag/$1/$2/agents"
  printf '%s\n' "$3" >"$ag/$1/$2/agents/openai.yaml"
}
agent_probe() { # <label> <trips|clears> <rule> <case> [triggers] [forked]
  local label="$1" want="$2" out got
  out=$(agent_check "$3" "$ag/$4" "${5:-}" "${6:-}" | grep '^FAIL')
  if [ -n "$out" ]; then got=trips; else got=clears; fi
  if [ "$got" = "$want" ]; then ok "probe: $label $want the check"
  else err "probe: $label — wanted '$want', got '$got': $out"; fi
}

echo "== user-invoked in every agent =="
# Claude Code and Kimi Code honour `disable-model-invocation: true`. Codex ignores the key and
# holds a skill back only when `agents/openai.yaml` beside its SKILL.md sets
# `policy.allow_implicit_invocation: false`, the file upstream's user-invoked skills carry.
# Without it, Codex may run `lab-edison` unasked and spend a credit. Both ways, as upstream's
# own rule has it: a skill is user-invoked in every agent or in none.
fx_ui='disable-model-invocation: true'
fx_optout='interface:
  display_name: "Fixture"
  short_description: "A fixture skill"
policy:
  allow_implicit_invocation: false'
fx_skill no-file fixture "A user-invoked fixture skill with no opt-out file." "$fx_ui"
fx_skill no-policy fixture "A user-invoked fixture skill whose file has no policy." "$fx_ui"
fx_openai no-policy fixture 'interface:
  display_name: "Fixture"'
fx_skill allowed fixture "A user-invoked fixture skill that Codex may still invoke." "$fx_ui"
fx_openai allowed fixture 'policy:
  allow_implicit_invocation: true'
fx_skill paired fixture "A user-invoked fixture skill paired the way upstream pairs it." "$fx_ui"
fx_openai paired fixture "$fx_optout"
fx_skill codex-only fixture "A model-invoked fixture skill that only Codex holds back."
fx_openai codex-only fixture "$fx_optout"
agent_probe "a user-invoked skill with no opt-out file"   trips  invocation no-file
agent_probe "an opt-out file with no policy"              trips  invocation no-policy
agent_probe "allow_implicit_invocation: true"             trips  invocation allowed
agent_probe "the key paired with upstream's opt-out file" clears invocation paired
agent_probe "an opt-out file on a model-invoked skill"    trips  invocation codex-only
agent_report "$(agent_check invocation skills)"

echo "== front-loaded descriptions =="
# Kimi Code lists a description over 250 characters as its first 247 and an ellipsis, so a
# trigger past that point never reaches it. Every lab-owned skill records the words a request
# uses when it wants that skill, and lint FAILS when Kimi's listing drops one. A report would
# change nothing: Kimi's cut is silent, and a skill it cannot find just never loads. The rows
# restate part of each description on purpose, so dropping a trigger takes a visible edit here.
#
# Lab-owned means every `lab-*` skill, `hq-mode`, and each skill forked in
# `upstream/attribution.json`; all three fail without a row. A tracked skill gets none: its
# description is upstream text, merged at each sync and never edited here. A trigger matches
# from a word start, ignoring case.
LAB_TRIGGERS='
lab-hpc: HPC, cluster, arc, chimera, ircbc, ssh, Slurm, sbatch, srun, squeue, compute, login, GPU, remote, files
lab-jupyter: Jupyter, notebook, tunnel, port forward, reconnect, cluster, compute node, GPU, arc, ircbc
lab-containers: Singularity, container, image, SIF, liulab-runtime, ircbc, pull, build, pixi, Jupyter, LIU_LAB_PACKAGES
lab-edison: Edison, literature, precedent, molecules, data analysis, Kosmos, dataset, recover, API key
lab-setup: set up, installing, Claude Code, auto-update, Codex, Kimi Code, marketplace clone, edison-cli, PATH
hq-mode: hq-mode, whole task, analysis, cluster run, figure, paper, grant, talk, experiment plan, tickets, working-style, playbook
bro: restate, last message, plain, jargon
ketchup: ketchup, catch, last message, action item, summary
technical-writing: technical, docs, README, RFC, protocol, PR description, commit message
unslop: AI tells, writing
lab-unslop-zh: 中文, 翻译腔, AI 味, 英译中, Chinese, translationese
'
fx_fill() { printf '%*s' "$1" '' | tr ' ' w; } # <n>: one filler word, n characters long
fx_skill early lab-fixture "Slurm $(fx_fill 300)"
fx_skill late lab-fixture "$(fx_fill 259) Slurm"
fx_skill ellipsis lab-fixture "$(fx_fill 244) Slurm $(fx_fill 20)"
fx_skill exact lab-fixture "$(fx_fill 244) Slurm"
fx_skill inside-word lab-fixture "Search the literature for this fixture."
fx_skill unrecorded lab-fixture "A lab-owned fixture skill with no triggers recorded."
fx_skill mode hq-mode "A mode fixture with no triggers recorded."
fx_skill tracked grilling "An adopted fixture skill, upstream text, so exempt."
fx_skill stale-row lab-fixture "Slurm fixture."
fx_row='lab-fixture: Slurm'
agent_probe "a trigger at the start"                    clears frontload early "$fx_row"
agent_probe "a trigger at character 261"                trips  frontload late "$fx_row"
agent_probe "a trigger under Kimi's ellipsis (246-250)" trips  frontload ellipsis "$fx_row"
agent_probe "a 250-character description, trigger last" clears frontload exact "$fx_row"
agent_probe "a trigger found only inside a word"        trips  frontload inside-word 'lab-fixture: arc'
agent_probe "a lab-* skill with no row"                 trips  frontload unrecorded
agent_probe "hq-mode with no row"                       trips  frontload mode
fx_skill forked unslop "A forked fixture skill with no triggers recorded."
agent_probe "a forked skill with no row"                trips  frontload forked '' unslop
agent_probe "a tracked skill with no row"               clears frontload tracked
agent_probe "a row for a skill that is not there"       trips  frontload stale-row "$fx_row
lab-gone: Slurm"
LAB_FORKED=$(python3 -c 'import json, re; print(*(m[1] for m in (re.fullmatch(r"skills/([^/]+)", k) for k in json.load(open("upstream/attribution.json"))) if m), sep=",")') \
  || err "upstream/attribution.json is unreadable, so no forked skill could be held to a row"
agent_report "$(agent_check frontload skills "$LAB_TRIGGERS" "$LAB_FORKED")"

rm -rf "$ag"
trap - EXIT

echo "== hq-mode =="
# The mode routes by name, so a name with nothing behind it is a dead end the agent meets only
# mid-task. One checker, `mode_check <rule> <args...>`, printing `FAIL<TAB>` or `ok<TAB>` lines as
# agent_check does and exiting 1 on any FAIL. Probed both ways on fixtures first.
#
#   index <index> <pages-dir> <what> [<heading>]   Every `- **name**` entry of the index (under
#       `## <heading>` when one is given, else anywhere in the file) has <pages-dir>/<name>.md,
#       and every page there has an entry. The playbook and principle indexes run it below;
#       another index inside the mode is one more `mode_run index ...` line.
#   skills <router> <skills-dir> <heading>   Every skill the trigger table names ships. A
#       backticked bare word under `## <heading>`, `/name` or `name`, is read as a skill name;
#       paths and file names, which hold a `.` or an inner `/`, are not. The upstream sync can
#       delete a skill, so "it shipped when the table was written" is not enough.
#   user <dir>   The text says "the user", never "hq": any lab member who types /hq-mode gets the
#       way of working applied to their own work. The name `hq-mode` is the one exception.
#   pause <page>   The always-pause list, under a heading naming it, still holds every item the
#       spec gave it, and still outranks every session override and every principle. This is
#       the text both hq-mode eval cases rest on; an edit that drops an item fails here, free.
mode_check() {
  python3 - "$@" <<'EOF'
import pathlib
import re
import sys

rule, args = sys.argv[1], sys.argv[2:]
failed = False


def say(verdict, msg):
    global failed
    failed = failed or verdict == "FAIL"
    print(f"{verdict}\t{msg}")


def section(path, heading):
    """The lines under `## <heading>` up to the next level-1 or level-2 heading; None if absent."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if heading is None:
        return lines
    for i, ln in enumerate(lines):
        if ln.strip() == f"## {heading}":
            rest = lines[i + 1:]
            end = next((j for j, r in enumerate(rest) if re.match(r"#{1,2} ", r)), len(rest))
            return rest[:end]
    return None


if rule == "index":
    index, pages, what = pathlib.Path(args[0]), pathlib.Path(args[1]), args[2]
    heading = args[3] if len(args) > 3 else None
    where = f"{index}" + (f" (## {heading})" if heading else "")
    lines = section(index, heading) if index.is_file() else None
    if lines is None:
        say("FAIL", f"no {what} index at {where}, so no {what} can be checked")
        sys.exit(1)
    named = [m[1] for m in (re.match(r"[-*] \*\*([a-z0-9]+(?:-[a-z0-9]+)*)", ln) for ln in lines) if m]
    have = {p.stem for p in pages.glob("*.md")}
    if not named:
        say("FAIL", f"the {what} index at {where} names no {what}: an entry is `- **<name>**`")
    for name in [n for n in named if n not in have]:
        say("FAIL", f"the {what} index at {where} names `{name}`, which has no page:"
                    f" add {pages}/{name}.md or drop the entry")
    for name in sorted(have - set(named)):
        say("FAIL", f"{pages}/{name}.md is a {what} the index at {where} doesn't name:"
                    f" add `- **{name}**` there, or delete the page")
    if named and not failed:
        say("ok", f"the {what} index at {where} and {pages}/ name the same {len(have)} {what}(s)")

elif rule == "skills":
    router, skills, heading = pathlib.Path(args[0]), pathlib.Path(args[1]), args[2]
    lines = section(router, heading) if router.is_file() else None
    if lines is None:
        say("FAIL", f"no `## {heading}` in {router}, so no skill it names can be checked")
        sys.exit(1)
    named = sorted({n.lstrip("/") for ln in lines
                    for n in re.findall(r"`(/?[a-z][a-z0-9]*(?:-[a-z0-9]+)*)`", ln)})
    gone = [n for n in named if not (skills / n / "SKILL.md").is_file()]
    for name in gone:
        say("FAIL", f"`## {heading}` in {router} names `{name}`, which no skill ships: route to"
                    f" a skill that does, or drop it. A backticked bare word there is a skill name")
    if not named:
        say("FAIL", f"`## {heading}` in {router} names no skill, so nothing was checked")
    elif not gone:
        say("ok", f"every skill `## {heading}` in {router} names ships ({len(named)})")

elif rule == "user":
    root, hits = pathlib.Path(args[0]), 0
    files = sorted(p for p in root.rglob("*") if p.suffix in (".md", ".yaml", ".yml"))
    if not files:
        say("FAIL", f"no text under {root}, so nothing was checked")
    for path in files:
        for n, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?<![A-Za-z0-9_])hq(?!-mode)(?![A-Za-z0-9_])", ln, re.IGNORECASE):
                hits += 1
                say("FAIL", f"{path}:{n} says \"hq\": the mode's text says \"the user\", so it"
                            f" applies to whoever types it. Only the name `hq-mode` may say hq")
    if files and not hits:
        say("ok", f"the text under {root} says \"the user\", never \"hq\" ({len(files)} files)")

elif rule == "pause":
    # Every item the spec gave the list, each as the words that must stay in it.
    ITEMS = (
        ("Slurm submit, run and cancel", ("sbatch", "srun", "scancel")),
        ("Edison spend", ("edison",)),
        ("the shared package store", ("package store",)),
        ("force-push", ("force-push",)),
        ("deleting data", (r"delet\w* data",)),
        ("wet-lab steps", ("wet-lab",)),
        ("merging an unreviewed PR without being told to land it", ("merg", "land it")),
        ("anything on a live service", ("live service",)),
        ("making private material public", ("private", "public")),
        ("editing the user's document beyond what they named", ("document",)),
        ("the list outranking every session override and every principle",
         ("outranks every session override", '"headless"', '"land it"', '"going to bed"',
          "every principle")),
    )
    page = pathlib.Path(args[0])
    lines = page.read_text(encoding="utf-8").splitlines() if page.is_file() else []
    start = next((i for i, ln in enumerate(lines)
                  if re.match(r"#+ .*always[- ]pause", ln, re.IGNORECASE)), None)
    if start is None:
        say("FAIL", f"no always-pause heading in {page}, so the list can't be checked")
        sys.exit(1)
    rest = lines[start + 1:]
    text = "\n".join(rest[:next((j for j, r in enumerate(rest) if r.startswith("#")), len(rest))])
    for label, words in ITEMS:
        lost = [w for w in words if not re.search(w.replace(" ", r"\s+"), text, re.IGNORECASE)]
        if lost:
            say("FAIL", f"the always-pause list in {page} has lost {label} (no {', '.join(lost)}):"
                        " every session override yields to that list, so an item off it is"
                        " an item nothing stops")
    if not failed:
        say("ok", f"the always-pause list in {page} holds all {len(ITEMS) - 1} items and"
                  " outranks every session override")

else:
    say("FAIL", f"mode_check has no rule `{rule}`")

sys.exit(1 if failed else 0)
EOF
}
mode_run() { # <rule> <args...>: reports through agent_report; a crash or silence is a FAIL
  local out rc
  out=$(mode_check "$@" 2>&1); rc=$?
  agent_report "$out"
  if [ "$rc" -ne 0 ] && ! printf '%s\n' "$out" | grep -q '^FAIL'; then err "mode_check $1 crashed: $out"
  elif [ -z "$out" ]; then err "mode_check $1 printed nothing, so it checked nothing"; fi
}
mf=$(mktemp -d "${TMPDIR:-/tmp}/lab-mode-fixtures.XXXXXX")
trap 'rm -rf "$mf"' EXIT
mode_probe() { # <label> <trips|clears> <rule> <args...>
  local label="$1" want="$2" out rc got; shift 2
  out=$(mode_check "$@" 2>&1); rc=$?
  if printf '%s\n' "$out" | grep -q '^FAIL'; then got=trips
  elif [ "$rc" -eq 0 ]; then got=clears
  else got="a crash"; fi
  if [ "$got" = "$want" ]; then ok "probe: $label $want the check"
  else err "probe: $label — wanted '$want', got '$got': $out"; fi
}
mkdir -p "$mf/pages"; : >"$mf/pages/a.md"; : >"$mf/pages/b.md"
printf '# Router\n\n## Triggers\n\n- **c**: not an entry\n\n## Playbooks\n\n### Kind\n\n- **a**: one\n- **b**: two\n\n## After\n\n- **d**: not an entry\n' >"$mf/router.md"
printf '# Index\n\n## Core\n\n- **a.** one\n\n## More\n\n- **b** (*lab edit*). two\n' >"$mf/whole.md"
printf '## Playbooks\n\n- **a**: one\n- **b**: two\n- **gone**: three\n' >"$mf/missing.md"
printf '## Playbooks\n\n- **a**: one\n' >"$mf/unnamed.md"
mode_probe "an index matching its pages"            clears index "$mf/router.md" "$mf/pages" playbook Playbooks
mode_probe "a whole-file index matching its pages"  clears index "$mf/whole.md" "$mf/pages" principle
mode_probe "an index entry with no page"            trips  index "$mf/missing.md" "$mf/pages" playbook Playbooks
mode_probe "a page the index doesn't name"          trips  index "$mf/unnamed.md" "$mf/pages" playbook Playbooks
mode_probe "an index under a heading that is not there" trips index "$mf/whole.md" "$mf/pages" playbook Playbooks
printf '# Index\n\n## Core\n\n- **a.** one\n- **b** (*lab edit*). two\n- **gone.** three\n' >"$mf/whole-missing.md"
mode_probe "a whole-file index entry with no page"  trips  index "$mf/whole-missing.md" "$mf/pages" principle
mkdir -p "$mf/skills/foo" "$mf/skills/bar"; : >"$mf/skills/foo/SKILL.md"; : >"$mf/skills/bar/SKILL.md"
cat >"$mf/shipped.md" <<'EOF'
## Triggers

Read its `SKILL.md`.

| When | Go to |
| --- | --- |
| x | `/foo`, then `bar`; see `AGENTS.md` and `references/x.md` |

## Next

`gone`
EOF
cat >"$mf/unshipped.md" <<'EOF'
## Triggers

| When | Go to |
| --- | --- |
| x | `/foo`, then `/gone` |
EOF
mode_probe "a trigger table naming skills that ship"   clears skills "$mf/shipped.md" "$mf/skills" Triggers
mode_probe "a trigger table naming a skill that doesn't" trips skills "$mf/unshipped.md" "$mf/skills" Triggers
mkdir -p "$mf/user/agents" "$mf/hq/agents"
cat >"$mf/user/SKILL.md" <<'EOF'
Read `hq-mode`'s page; work the user's way.
EOF
printf 'display_name: "hq-mode"\n' >"$mf/user/agents/openai.yaml"
printf 'Work the way the user does.\n' >"$mf/hq/SKILL.md"
printf 'display_name: "HQ Mode"\n' >"$mf/hq/agents/openai.yaml"
mode_probe "text naming the user"                    clears user "$mf/user"
mode_probe "an opt-out file calling the mode HQ"     trips  user "$mf/hq"
cat >"$mf/pause.md" <<'EOF'
# Working style

### Always pause

This list outranks every session override ("headless", "land it", "going to bed") and every
principle.

- `sbatch`, `srun`, `scancel`.
- Any Edison spend.
- The shared package store.
- Force-push; deleting data.
- Merging a PR nobody reviewed unless told to land it.
- Anything on a live service.
- Making private material public.
- Wet-lab steps.
- Editing the user's document beyond what they named.

### Next

- wet-lab, again
EOF
grep -v '^- Wet-lab' "$mf/pause.md" >"$mf/no-wet-lab.md"
grep -v 'outranks' "$mf/pause.md" >"$mf/no-rank.md"
mode_probe "an always-pause list holding every item" clears pause "$mf/pause.md"
mode_probe "an always-pause list without wet-lab steps" trips pause "$mf/no-wet-lab.md"
mode_probe "an always-pause list that outranks nothing" trips pause "$mf/no-rank.md"
rm -rf "$mf"
trap - EXIT

mode_run index skills/hq-mode/SKILL.md skills/hq-mode/references/playbooks playbook Playbooks
mode_run index skills/hq-mode/references/principles.md skills/hq-mode/references/principles principle
mode_run skills skills/hq-mode/SKILL.md skills Triggers
mode_run user skills/hq-mode
mode_run pause skills/hq-mode/references/working-style.md

echo "== Chinese length caps =="
# vale's `words` counter cannot measure Chinese and cannot be made to. It treats a run of
# characters between two full-width commas as one word, so, measured on this repo's own
# configuration: 420 Chinese characters count as 40 words, 1260 as 120, 4200 as 400. A Chinese
# SKILL.md would therefore pass the 600-word cap at roughly 6000 characters, about ten times
# the English budget, and the ratio moves with punctuation density rather than with length.
#
# So the Chinese caps are counted here, in CJK codepoints, and `.vale.ini` is left exactly as
# it was: its English caps still apply to every file and simply never fire on a Chinese one.
# See docs/adr/0015-chinese-caps-are-counted-in-lint.md.
#
# A file counts as Chinese when its CJK codepoints outnumber its ASCII letters, so a page that
# merely quotes a Chinese term keeps the English cap and is not touched here.
zh_check() { # <skills-dir>: prints ok/FAIL lines, one per Chinese file
  python3 - "$1" <<'EOF'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
# Same split as .vale.ini sections 2 and 3: a body is an interface, its pages hold the detail.
CAPS = (("*/SKILL.md", 1000), ("*/references/**/*.md", 2000))
CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
LATIN = re.compile(r"[A-Za-z]")

for pattern, cap in CAPS:
    for p in sorted(root.glob(pattern)):
        text = p.read_text(encoding="utf-8")
        n, latin = len(CJK.findall(text)), len(LATIN.findall(text))
        if n <= latin:
            continue
        if n > cap:
            print(f"FAIL\t{p.as_posix()} is {n} Chinese characters; the cap is {cap}."
                  " Cut it, or move detail into references/")
        else:
            print(f"ok\t{p.as_posix()} is {n}/{cap} Chinese characters")
EOF
}
zh=$(mktemp -d "${TMPDIR:-/tmp}/lab-zh-fixtures.XXXXXX")
trap 'rm -rf "$zh"' EXIT
fx_zh() { # <case> <path-under-skill> <hanzi> <latin-words>
  mkdir -p "$(dirname "$zh/$1/lab-fixture/$2")"
  python3 -c 'import sys; p,h,w=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]);
open(p,"w",encoding="utf-8").write("# 标题\n\n"+"常态"*(h//2)+"\n\n"+"word "*w)' \
    "$zh/$1/lab-fixture/$2" "$3" "$4"
}
zh_probe() { # <label> <trips|clears> <case>
  local out got
  out=$(zh_check "$zh/$3" | grep '^FAIL')
  if [ -n "$out" ]; then got=trips; else got=clears; fi
  if [ "$got" = "$2" ]; then ok "probe: $1 $2 the check"
  else err "probe: $1 — wanted '$2', got '$got': $out"; fi
}
fx_zh body-over SKILL.md 1200 0
fx_zh body-under SKILL.md 900 0
fx_zh ref-over references/page.md 2500 0
fx_zh ref-under references/page.md 1900 0
fx_zh english SKILL.md 40 4000
zh_probe "a Chinese skill body over 1000 characters"  trips  body-over
zh_probe "a Chinese skill body under 1000 characters" clears body-under
zh_probe "a Chinese reference page over 2000"         trips  ref-over
zh_probe "a Chinese reference page under 2000"        clears ref-under
zh_probe "an English page quoting a few Chinese terms" clears english
agent_report "$(zh_check skills)"
rm -rf "$zh"
trap - EXIT

echo "== release =="
# The version has to identify the content. This plugin's source is the repo ROOT, so
# `claude plugin update` clones the whole tree — tests, docs and tooling included — and two
# commits declaring the same version but differing in any tracked file are two different
# installs wearing one number. That is not hypothetical: 2026.9.3 was tagged, test-only
# changes merged on top without a bump, and the plugin cache and origin/main both reported
# 2026.9.3 with different bytes. So an already-tagged version must name this exact tree.
pver=$(python3 -c 'import json; print(json.load(open(".claude-plugin/plugin.json"))["version"])' 2>/dev/null)
if [ -z "$pver" ]; then
  err "cannot read version from .claude-plugin/plugin.json"
elif [ -z "$(git tag -l 'v*' 2>/dev/null)" ]; then
  # Silence is not success. A shallow clone with no tags would sail through the branches
  # below by having nothing to compare against, so the missing input is itself the failure.
  # CI checks out with fetch-depth: 0 to give this rule something to read.
  err "no v* tags visible, so the release rule cannot run (CI needs fetch-depth: 0)"
elif ! git rev-parse -q --verify "refs/tags/v$pver" >/dev/null 2>&1; then
  ok "version $pver is not tagged yet — an unreleased bump"
elif git diff --quiet "v$pver" -- . 2>/dev/null; then
  ok "version $pver matches tag v$pver"
else
  err "version $pver is already tagged v$pver but the tree has moved — bump the version. Changed: $(git diff --name-only "v$pver" -- . | tr '\n' ' ')"
fi

# The Edison command's own self-test used to live here. It shadowed `uv` on PATH with a
# shell stub, and deleting `skills/lab-edison/scripts/edison-task.sh` deleted that seam along
# with the script. The same four properties are now asserted in `tests/edison_cli/`, against a
# fake `edison_client` package the test writes and puts first on PYTHONPATH:
#
#   * refusals for an absent query file, an empty one and a job name off the routing table,
#     exit 2, before the preflight is reached — `test_refusals.py`;
#   * every network-touching subcommand refusing with exit 1 and relaying the preflight's own
#     remedy, asserted through the placeholder — `test_refusals.py`;
#   * the identifier as the first line of stdout — `test_key_discipline.py`;
#   * the key arriving in the client's environment and appearing in no argument, no program
#     text and no output — `test_key_discipline.py`.
#
# They run under `pixi run test`, which is a step of `check-static`, so `pixi run check` still
# asserts all four. The stub principle is unchanged: a test of the spending path must be safe
# on the day the path is broken.

echo "== eval guard self-test =="
# These lines RUN tests/eval.sh. If its guard ever regressed they would launch real headless
# sessions and spend tokens from inside `pixi run check` — the exact failure the guard exists
# to prevent, set off by the test for it. So `claude` is shadowed by a stub that spends
# nothing and records every call. The test is then safe when the guard is broken, and it can
# assert the stub was never reached, which is a stronger claim than an exit code alone.
gd=$(mktemp -d "${TMPDIR:-/tmp}/lab-eval-guard.XXXXXX")
trap 'rm -rf "$gd"' EXIT
mkdir -p "$gd/bin"
printf '#!/bin/sh\necho "$@" >>"%s/claude-calls"\n' "$gd" >"$gd/bin/claude"
chmod +x "$gd/bin/claude"

guard_case() { # <label> <eval.sh args...>
  local label="$1"; shift
  local out rc
  out=$(PATH="$gd/bin:$PATH" bash tests/eval.sh "$@" 2>&1)
  rc=$?
  if [ "$rc" -eq 2 ] && printf '%s' "$out" | grep -q "Nothing was run"; then
    ok "eval guard: $label is refused"
  else
    err "eval guard: $label — wanted exit 2 and a refusal, got exit $rc: $out"
  fi
}

# The four ways to ask for nothing runnable. A bare run is the one that matters most: it is
# what an agent types when it decides to "just run the tests".
guard_case "a bare run"
guard_case "--live on its own" --live
guard_case "an unknown case name" --only nope
guard_case "--only beside --all" --only trigger --all

if [ -s "$gd/claude-calls" ]; then
  err "eval guard: a refused invocation still launched $(grep -c . "$gd/claude-calls") claude session(s)"
else
  ok "eval guard: no refused invocation launched a session"
fi
rm -rf "$gd"
trap - EXIT

echo "== eval assertions =="
# Test the eval regexes without an API call. `--dump` prints the assertions the harness
# actually uses, so this checks THOSE and not a copy that would drift out of step with them.
# Every fixture here is synthetic; several are regressions from a run that was correct and
# was reported as failed.
fixdir=tests/fixtures/eval
dump=$(bash tests/eval.sh --dump 2>/dev/null)
if [ -z "$dump" ]; then
  err "tests/eval.sh --dump printed nothing, so no assertion could be checked"
else
  covered=0
  uncovered=""
  # Heredoc, not a pipe: a piped `while` runs in a subshell, where `err` would set `fail`
  # on a copy of it and every failure below would vanish at the closing `done`.
  while IFS="$(printf '\037')" read -r cname cexp cdeny calso; do
    [ -n "$cname" ] || continue
    hasfx=0
    # Every fixture the case has, each tested on its own. A suffix may carry a label,
    # `<case>.fail-deny-close.txt`, so one rule can hold two transcripts that it must each
    # catch: one fixture holding both would pass with only half of the regex working.
    for fixture in "$fixdir/$cname".*.txt; do
      [ -f "$fixture" ] || continue
      hasfx=1
      kind=${fixture##*/}; kind=${kind#"$cname".}; kind=${kind%.txt}
      case "$kind" in
        pass | pass-?*)
          if grep -qiE "$cexp" "$fixture"; then ok "$cname: $kind fixture matches expect"
          else err "$cname: $kind fixture does not match its expect regex"; fi
          if [ -n "$cdeny" ]; then
            if grep -qiE "$cdeny" "$fixture"; then err "$cname: $kind fixture trips its DENY"
            else ok "$cname: $kind fixture clears its DENY"; fi
          fi
          if [ -n "$calso" ]; then
            if grep -qiE "$calso" "$fixture"; then ok "$cname: $kind fixture matches its ALSO"
            else err "$cname: $kind fixture does not match its ALSO regex"; fi
          fi ;;
        fail-also | fail-also-?*)
          if [ -z "$calso" ]; then err "$cname: has a $kind fixture but no ALSO assertion"
          elif grep -qiE "$calso" "$fixture"; then err "$cname: $kind fixture wrongly matches its ALSO"
          else ok "$cname: $kind fixture correctly misses its ALSO"; fi ;;
        fail-expect | fail-expect-?*)
          if grep -qiE "$cexp" "$fixture"; then err "$cname: $kind fixture wrongly matches expect"
          else ok "$cname: $kind fixture correctly misses expect"; fi ;;
        fail-deny | fail-deny-?*)
          if [ -z "$cdeny" ]; then err "$cname: has a $kind fixture but no DENY assertion"
          elif grep -qiE "$cdeny" "$fixture"; then ok "$cname: $kind fixture trips its DENY"
          else err "$cname: $kind fixture does not trip its DENY"; fi ;;
        # A misspelt suffix would otherwise be a fixture that nothing reads.
        *) err "$cname: $fixture has no fixture suffix lint knows (see $fixdir/README.md)" ;;
      esac
    done
    if [ "$hasfx" -eq 1 ]; then covered=$((covered + 1)); else uncovered="$uncovered $cname"; fi
  done <<EOF
$dump
EOF
  ok "fixtures cover $covered eval case(s)"
  [ -n "$uncovered" ] && echo "  note: no fixtures yet for:$uncovered"
fi

echo "== eval case lists =="
# Three places name the eval cases: the usage comment, the "no cases matched" line and
# tests/README.md. AGENTS.md was a fourth until it became a page of pointers. All four were
# stale before anyone noticed — tests/README.md had been missing `reuse-job` through two
# releases — because keeping them in step was a habit and not a check. It is a check now.
# Lives here rather than in the conformance checker because the case list comes from
# `--dump`, which is this file's business.
if [ -z "${dump:-}" ]; then
  err "no case list to check (tests/eval.sh --dump printed nothing)"
else
  listfail=0
  for f in tests/eval.sh tests/README.md; do
    [ -f "$f" ] || { err "$f is missing, so its eval case list cannot be checked"; listfail=1; continue; }
    missing=""
    while IFS="$(printf '\037')" read -r cname _rest; do
      [ -n "$cname" ] || continue
      grep -qF -- "$cname" "$f" || missing="$missing $cname"
    done <<EOF
$dump
EOF
    if [ -n "$missing" ]; then
      err "$f does not name these eval cases:$missing"
      listfail=1
    fi
  done
  [ "$listfail" -eq 0 ] && ok "every eval case is named in eval.sh and tests/README.md"
fi

echo
if [ $fail -eq 0 ]; then echo "LINT PASS"; else echo "LINT FAIL"; fi
exit $fail
