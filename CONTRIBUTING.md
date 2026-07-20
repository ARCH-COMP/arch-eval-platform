# Contributing

This repo is the **ARCH-COMP variant** of the
[core evaluation platform](https://github.com/TUMcps/core-eval-platform): the `arch_comp` plugin app
plus its deploy config. An ARCH tool defines a Docker base image; the engine clones the tool in,
installs it, then runs each benchmark category's instances. All the heavy lifting lives in core;
this repo holds the ARCH-specific seams, category specs, step handlers, and node scripts.

## The core submodule

The core engine is vendored as a git submodule at `./core`, pinned to a specific commit for
reproducible dev and deploy. A recursive clone brings it along; if you already have a checkout
without it:

```bash
git submodule update --init
```

The compose stack mounts `./core` (backend) and `./core/frontend` (Vite), so a normal
`docker compose up --build` runs against the pinned core with hot reload.

### Updating the pinned core

Move the pin with the helper shipped in core, then commit the change:

```bash
core/scripts/bump-core.sh          # latest core main
core/scripts/bump-core.sh dev      # ...or a branch, tag, or commit
git commit -m "chore: bump core"   # records the new pin
```

When a change spans both repos, merge the core change first, then bump this repo's pin to it.

## Tests

```bash
docker run --rm -v "$PWD/core:/core" -v "$PWD:/arch" -w /arch python:3.11-slim \
  sh -c "pip install -q -e '/core[dev]' -e /arch && pytest"
```
