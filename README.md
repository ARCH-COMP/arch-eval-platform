# ARCH-COMP

The **ARCH-COMP** variant of [comp-eval-platform](https://github.com/TUMcps/core-eval-platform): the `arch_comp` plugin
app plus its deploy config, depending on the core engine. An ARCH tool defines a Docker base
image; the engine clones the tool in, installs it, then runs each benchmark category's instances.
All the heavy lifting lives in core; this repo is the ARCH-specific seams, category specs, step
handlers, and node scripts.

## Requirements

- Docker + Docker Compose (Docker Desktop on macOS/Windows). The backend mounts the host Docker
  socket to run worker containers.
- Git.

## Getting started

Clone this repo and the core engine **side by side** under the same parent directory (the compose
file mounts `../comp-eval-platform`):

```bash
git clone https://github.com/TUMcps/core-eval-platform.git   comp-eval-platform
git clone https://github.com/ARCH-COMP/arch-eval-platform.git   arch-comp-new
cd arch-comp-new && docker compose up --build
```

- Frontend: <http://localhost:5174>  (one above the VNN stack, so both run side by side)
- Public URL (optional): `docker compose logs cloudflared | grep trycloudflare`

The backend installs core + this plugin, migrates, seeds settings, and serves. The **first
account you sign up becomes the admin**; later signups start disabled until an admin enables them.

## Tests

```bash
docker run --rm -v "../comp-eval-platform:/core" -v "$PWD:/arch" -w /arch python:3.11-slim \
  sh -c "pip install -q -e '/core[dev]' -e /arch && pytest"
```
