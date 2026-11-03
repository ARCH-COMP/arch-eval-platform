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

## Production deployment (cpsvm5 + Glados)

The live ARCH site runs on two machines:

| Part | Machine | Folder | Compose project |
| --- | --- | --- | --- |
| Website (Postgres, backend, frontend, SSH tunnel) | `cpsvm5.cit.tum.de` | `/opt/arch-comp-v2` | `arch-comp` |
| Worker (`worker_service`, starts one container per submission) | `glados.cps.in.tum.de` | `/home/gupe/arch-eval-platform` | `arch-comp` |

```
browser ──https──▶ host proxy (arch-caddy) ──▶ frontend / backend (cpsvm5)
backend ──▶ worker-tunnel ──ssh -L──▶ Glados 127.0.0.1:9001   (worker_service)
backend ──ssh -J Glados──▶ job container 172.30.x.x            (per-step scripts)
job container ──ROOT_URL──▶ /update callbacks
```

The worker service has no authentication and controls Docker, so it only listens on
Glados' loopback. The website reaches it, and the job network, through SSH as the worker
account, using a key that is limited to forwarding
(`restrict,port-forwarding` in `~/.ssh/authorized_keys`). Website and worker must run the
same pinned `core` version (`git -C core rev-parse HEAD` on both).

### Worker (Glados)

Glados has Docker 20.10 and `docker-compose` 1.29 (no `docker compose`), and the account
must be in the `docker` group.

```bash
git clone --recurse-submodules https://github.com/ARCH-COMP/arch-eval-platform.git
cd arch-eval-platform
docker-compose -p arch-comp -f deploy/production/compose.worker.yml up -d --build
curl http://127.0.0.1:9001/health        # {"ok": true}
```

The container restarts automatically (`restart: unless-stopped`). Job containers are named
`arch-<id>` on the network `arch-comp-jobs` (`172.30.0.0/16`). To update:

```bash
git pull --ff-only && git submodule update --init
docker-compose -p arch-comp -f deploy/production/compose.worker.yml up -d --build
```

Other users' containers on Glados (`crw-*`, `cobra-*`, `onyx-*`, ...) are unrelated.

### Website (cpsvm5)

`/opt/arch-comp-v2/docker-compose.override.yml` is not in git. Besides the proxy settings it
adds the tunnel and the worker address:

```yaml
services:
  backend:
    volumes:
      - ./ssh/config:/root/.ssh/config:ro
      - ./ssh/id_worker:/root/.ssh/id_worker:ro
      - ./ssh/known_hosts:/root/.ssh/known_hosts:ro
      - ./ssh/comp.pem:/root/.ssh/comp.pem
    environment:
      REMOTE_DOCKER_WORKER_URL: worker-tunnel
      REMOTE_DOCKER_WORKER_PORT: "9001"
      EVAL_SERVICE_ID: arch-comp
  worker-tunnel:
    image: alpine:3.20
    restart: unless-stopped
    volumes:
      - ./ssh:/etc/arch-ssh:ro
    command: >
      sh -c "apk add --no-cache openssh-client >/dev/null &&
             install -d -m 700 /root/.ssh &&
             cp /etc/arch-ssh/config /etc/arch-ssh/id_worker /etc/arch-ssh/known_hosts /root/.ssh/ &&
             chmod 600 /root/.ssh/config /root/.ssh/id_worker /root/.ssh/known_hosts &&
             exec ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 0.0.0.0:9001:127.0.0.1:9001 arch-worker"
```

`/opt/arch-comp-v2/ssh/` (never committed, root-only) holds:

- `id_worker`: key authorized on Glados (forwarding only); `comp.pem`: key for the job
  containers, kept so it survives container recreation;
- `known_hosts`: Glados' host keys (`ssh-keyscan glados.cps.in.tum.de`);
- `config`:

```
Host arch-worker
    HostName glados.cps.in.tum.de
    User gupe
    IdentityFile /root/.ssh/id_worker
    IdentitiesOnly yes
    ServerAliveInterval 30

Host 172.30.*
    ProxyJump arch-worker
    UserKnownHostsFile /dev/null
    LogLevel ERROR
```

Check the connection from the website:

```bash
docker compose exec backend curl -sS http://worker-tunnel:9001/health
```

The scheduler and the parallel-job limit (currently 1) are set in Admin → Settings.

### Old ARCH system (stopped, kept)

The former ARCH stack on cpsvm5 (`/opt/arch/submission-system`) and its Celery workers on
Glados (`arch-submission-worker`, `arch-unzip-worker`, started from
`/home/crwbot/submission-system/docker/prod`, plus `gitlab-runner-arch`) are stopped or
unused. They cannot serve this platform and were left untouched.

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
