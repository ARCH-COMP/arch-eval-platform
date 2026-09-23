# Migration from the legacy ARCH system

The old wiki describes a different application. It is retained only as historical input;
these documents describe the current plugin and shared core.

## Feature mapping

| Legacy concept | Current status or replacement |
| --- | --- |
| ZIP upload and `submit.sh` | Removed. Tools and benchmarks are Git repositories with structured interfaces. |
| RabbitMQ/Celery worker queues | Removed. Core uses an APScheduler control loop and provisioned workers. |
| Separate unzip and execution workers | Removed. A task owns an ordered plugin-defined step graph. |
| MinIO submission/result buckets | Removed. Metadata and normalized results live in PostgreSQL; local/remote Git repos hold configured exports. |
| MinIO category secret injection | Not available. The current platform contains no category secret-delivery mechanism. |
| Published-submission Git push button | Not available. ARCH task results can be downloaded; no official publication workflow is included. |
| Multiple conference pages in one frontend | Replaced by one active competition plugin per deployment and a shared frontend shell. |
| Binary admin flag | Replaced by `user`, `organizer`, and `admin` roles. |
| Legacy Django admin model operations | Replaced by current core catalog/task models and shared UI controls. |
| GitLab runner pipeline | Replaced by GitHub Actions. |
| Host cron database backup | Not shipped. Backups are a deployment responsibility described by core. |
| Old server/container map | Obsolete. Current public documentation contains no deployment-specific infrastructure map. |

## Concepts retained in the current system

- reproducible ARCH submissions;
- category-specific instance and result formats;
- operator recovery goals expressed through PostgreSQL and current persistent storage;
- general deployment lessons that do not depend on retired services.

Old command lines, API paths, model names, service names, and host layouts do not describe
the current system.

## Credential incident rule

The legacy wiki contained plaintext operational credentials. They have intentionally not
been transferred here. Any credential ever present in that repository must be treated as
exposed and rotated; deleting or editing the wiki page does not remove it from Git history
or existing clones.

Private runbooks may reference secret-manager entry names without containing secret values.
