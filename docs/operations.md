# Operations

Shared deployment, security, scheduler, administration, and backup guidance lives in the
[core documentation](https://github.com/TUMcps/core-eval-platform/tree/main/docs). This
page contains only ARCH repository specifics.

## Local development

Clone recursively and start the Compose stack:

```bash
git clone --recurse-submodules https://github.com/ARCH-COMP/arch-eval-platform.git
cd arch-eval-platform
docker compose up --build
```

The frontend is available at `http://localhost:5174`. The backend container runs migrations,
initializes runtime settings, and starts Django. The first signup becomes the enabled admin.

The stack uses PostgreSQL, the shared frontend from the pinned `core` submodule, a persistent
data volume, and `local_docker` workers. It mounts the host Docker socket so the backend can
create worker containers.

## Dedicated Docker worker

For `remote_docker`, run the worker service from the same pinned repository version on the
worker machine:

```bash
docker compose run --rm -p 9001:9001 backend \
  python deploy/manage.py worker_service --host 0.0.0.0 --port 9001
```

Then select `remote_docker` in Admin > Settings and configure the global worker address or a
user-specific override. Restrict the worker service to trusted network access; it has no
built-in authentication or TLS.

## CI and core updates

GitHub Actions runs ARCH tests, pinned core tests, frontend checks/build, Compose validation,
and a backend-image build. There is no GitLab runner requirement in the current repository.

The core engine is pinned as a submodule. Update it with:

```bash
core/scripts/bump-core.sh
git commit -m "chore: bump core"
```

When a change spans core and ARCH, merge the core change first, then bump the ARCH pin.

## ARCH checks after a change

1. Load a small category repository and confirm its benchmarks and instances are replaced
   as expected.
2. Run the example tool against at least one benchmark in each affected category.
3. Confirm live logs and partial result progress appear.
4. Download the completed task bundle and inspect the raw CSV.
5. Confirm AINNCS extra timing fields parse when applicable.
6. Confirm the worker is removed after shutdown.

## Current limitations

- No legacy ZIP upload or `submit.sh` compatibility layer.
- No MinIO secret-data injection.
- No automatic push of published submissions to the former repeatability repository.
- No separate conference-page generator.
- No repository-provided automated database backup job.
- The AWS adapter is not turnkey without deployment-supplied lifecycle scripts and cloud
  configuration.
