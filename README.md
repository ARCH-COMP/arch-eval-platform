# ARCH-COMP

The submission and evaluation platform for **ARCH-COMP**, the international competition on the
verification of continuous and hybrid systems. Submit a tool or a benchmark; the platform
provisions a worker, runs it, collects logs, and scores the results. Built on the shared
[core evaluation platform](https://github.com/TUMcps/core-eval-platform).

## Requirements

- Docker + Docker Compose (Docker Desktop on macOS/Windows).
- Git.

## Getting started

```bash
git clone --recurse-submodules https://github.com/ARCH-COMP/arch-eval-platform.git
cd arch-eval-platform && docker compose up --build
```

- Frontend: <http://localhost:5174>
- Public URL (optional): `docker compose logs cloudflared | grep trycloudflare`

The **first account you sign up becomes the admin**; later signups start disabled until an admin
enables them.

## Contributing

Developing the platform (tests, updating the core engine, architecture) is covered in
[CONTRIBUTING.md](CONTRIBUTING.md).
