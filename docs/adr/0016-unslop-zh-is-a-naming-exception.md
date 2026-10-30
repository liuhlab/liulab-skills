---
search:
  exclude: true
---

# `unslop-zh` is the second lab-owned naming exception

The two Chinese-writing skills merge into one lab-owned skill named `unslop-zh`. The maintainer
chose the bare name to pair it with `unslop` and make the language choice clear. It does not
become an adopted skill and gets no upstream record. `hq-mode` remains the only other exception
to the `lab-*` name for skills the lab wrote or derived.

## What it costs

A project or user skill with the same bare name can shadow the lab copy without a warning.
`/lab-setup` reports such copies and removes none. Lint names both exceptions explicitly and
still requires `unslop-zh` to record its triggers; no other unrecorded bare name passes.

## What this reverses

ADR 0013's statement that `hq-mode` is the one exception. Its rule that adopted skills keep
their upstream names stands, as does the rejection of renaming adopted skills to `lab-*`.
