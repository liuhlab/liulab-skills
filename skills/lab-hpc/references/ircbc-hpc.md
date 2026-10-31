# ircbc — hosts, network, toolchain, storage

What the machines are and what they can reach. Partitions and submitting are in `ircbc-slurm.md`; the rule about where work runs is
`SKILL.md`'s. Every host below is an `~/.ssh/config` alias — resolve the details from that file at run time, never record them. CentOS 7.6
(glibc 2.17) with Slurm 18.08: an old cluster, and it shows. Modern binaries will not run on the bare host, so real work goes inside a
Singularity image (`lab-containers`).

## VPN — stop and ask

The whole cluster sits behind a **VPN** (the atrust app) that the user manages by hand. If ssh to `ircbc` or any node hangs or times out,
**stop and tell the user to check or re-login the VPN**. Do not retry in a loop, look for another route, or try to fix it yourself.

## Hosts and reaching a compute node (verified 2026-09-04)

- **Login:** `ircbc`. A doorway. Two reasons to be here (`SKILL.md`): submitting your first job, and the two things compute nodes lack —
  internet and `git`.
- **Compute:** `cpu01`…`cpu08`, ProxyJumping through `ircbc`.
- **Transfer:** `ircbc-transfer` — separate shared lab account, direct internet, local disk of its own, but it does **not mount `/share`**,
  so it cannot see lab code or the image store. Fetch there and copy over; never compute there. It does have `git` and `rsync`.

**ircbc has no `pam_slurm_adopt` gate.** ssh to a `cpu0X` alias connects even with `squeue -u $USER` empty, so sweeping the eight aliases
finds a reachable node fast — and a trap, because **reachable never means permitted**. Working on a node you hold no allocation for
steals CPU from the job the scheduler put there. Nothing technical stops you; this rule does. arc does enforce it.

Only some `cpu0X` aliases are in `known_hosts`; the rest fail under `BatchMode` with `Host key verification failed`, so probe with
`-o StrictHostKeyChecking=accept-new`. And **every** cpu-alias connection prints `port 22: Network is unreachable` on stderr and *then
succeeds* — the jump tries a dead address first. Judge by exit status, never by scanning stderr, or you will retry a working link forever.

## What compute nodes lack: internet and `git` (verified 2026-09-04)

| Host | Internet | Notes |
| --- | --- | --- |
| `cpu01`…`cpu08` | **none** | Confirmed: `curl https://github.com` returns http_code 000. Stage every download first; a job must never assume network. |
| `ircbc` | via SOCKS proxy | `socks5h://<login-host>:1080`, exported by the shell profile, so `curl` and `git` just work. `ghcr.io/v2/` answers 401, the expected unauthenticated challenge, and `git ls-remote` returns real SHAs. |

**The proxy-env trap.** Six variables — `http_proxy`, `https_proxy`, `all_proxy` and their uppercase twins — point at a port only the login
node listens on, and `sbatch`/`srun` propagate them into jobs. A fetch on a compute node then fails as *connection refused on port 1080*,
which reads like a broken proxy but means "no internet here". `unset` all six at the top of a job script so tools fail honestly, and
`curl --noproxy '*'` to probe localhost.

| Tool | `ircbc` login | `cpu0X` compute |
| --- | --- | --- |
| `git` | present | **absent, and no module for it** |
| `rsync`, `python3`, `pixi`, `uv`, `module` | present | present, `module` included even non-interactively |
| `singularity` | module only, `singularity/3.2.1` | same module, an old 3.x — `module avail singularity` if that name has moved |
| `crane`, `conda` / `mamba` | `crane` in the image store, and useful | `crane` useless (no internet); no conda or mamba |

The missing `git` is the one that bites: even an offline `git status` or `git log` needs a login-node hop. Drive git from `ircbc` against
`/share`, or put git inside your container or pixi env so compute-side sessions stand alone. Compute PATH is bare — `~/.pixi/bin:/usr/local/bin:/usr/bin:/opt/ibutils/bin`.

**rclone: not the module's.** The module rclone reads a system `rclone.conf` that users cannot read, so it fails with
`permission denied`. Run the project environment's rclone (`pixi run rclone`) and set `RCLONE_CONFIG` to a config file you own.
Your remotes, paths and destinations go in `~/.claude/lab/personal.md`, never in this repo.

## Storage and the `$LIU_LAB_PACKAGES` image store

`/share` is mounted and writable on login and compute alike. It is the big shared filesystem and it does fill up — `df -h /share` before
writing large outputs or pulling an image, and never assume the headroom is there. Lab code lives in `/share/home/<user>/src`, one
directory per repo, names matching local ones, synced local → GitHub → `git pull`; `rsync`/`scp` from a laptop through `ircbc` lands
straight on `/share` (2026-07-05). `$LIU_LAB_PACKAGES` is set on both hosts and the store sits on `/share`, so jobs can read the images;
only the network *fetch* is login-bound. It holds the `*.sif` images, a `*.sif.digest` sidecar each (a `sha256:` line, compared against
`crane digest` for updates), `bin/` (`crane`, smoke-test scripts), `oci/` (transient tarballs) and `logs/`. Which images exist changes —
**list the store rather than assuming**. It is group-writable with setgid dirs so any member can add images; keep it that way.
