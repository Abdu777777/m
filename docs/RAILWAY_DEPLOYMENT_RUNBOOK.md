# Railway deployment runbook — Arab Option

This runbook is a configuration guide, not evidence that a Railway deployment has been created or verified. Do not upload real identity documents or accept real payments until the checks below are completed in the deployed environment.

## 1. Required environment variables

Configure these in Railway's service Variables panel. Never commit production values to Git.

| Variable | Production guidance |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | Generate a unique random secret of at least 50 characters. Do not reuse the CI value or examples from this repository. |
| `ALLOWED_HOSTS` | Comma-separated exact hostnames, without scheme or path, e.g. `app.example.com`. Include the assigned Railway hostname only if it is used. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated full HTTPS origins, e.g. `https://app.example.com`. |
| `DATABASE_URL` | Railway PostgreSQL connection URL. Verify backups and restore procedures separately. |
| `SECURE_SSL_REDIRECT` | Keep `True` only after HTTPS and Railway proxy headers have been verified. |
| `MEDIA_ROOT` | If using a persistent Railway Volume, set to a path inside the mounted volume, e.g. `/data/private-media`. |

The project uses `Asia/Aden` as its configured time zone. Keep secrets in Railway Variables, not in source files, build logs, or screenshots.

## 2. Identity-document storage (KYC)

KYC documents contain sensitive personal information. The default filesystem storage is not a persistent or access-controlled storage service by itself.

Choose and verify one storage design before enabling KYC in production:

### Option A — Persistent private volume

1. Attach a Railway Volume to the application service.
2. Mount it at `/data` and set `MEDIA_ROOT=/data/private-media`.
3. Ensure the directory is writable by the application process.
4. Verify the volume is not exposed by a static-file server, reverse proxy, or public route.
5. Test that an unauthenticated visitor and a different account cannot download a document.
6. Back up the volume securely and test a restore.

A volume can preserve files across deployments, but it is not automatically a backup and may not be shared across multiple service replicas.

### Option B — Private S3-compatible object storage

Set `USE_S3_MEDIA=True` and configure the required `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, and `AWS_S3_REGION_NAME` variables. Use a private bucket, least-privilege credentials, and short-lived signed URLs. The application is configured to sign media URLs for a five-minute period; verify actual access behavior with the chosen provider.

Do not use public-read ACLs or public bucket policies. Confirm that the provider's endpoint and signing implementation are compatible before storing real documents.

The upload validator checks file size, extension, and a basic file signature only. It is not malware scanning, document sanitization, or a full PDF/image parser.

## 3. Build, migration, and health check

- Install dependencies from `requirements.txt`.
- Use the project's production application server command configured for the service (Gunicorn with `config.wsgi`).
- Apply Django migrations as a controlled release step; verify the database backup before schema changes.
- Configure the health check path as `/health/`.
- Run `python manage.py check --deploy` with the same non-secret production settings before launch.
- Verify HTTPS redirect behavior and the `X-Forwarded-Proto` header on Railway before relying on proxy SSL configuration.

## 4. Pre-launch verification

- [ ] `DEBUG=False` and a unique production `SECRET_KEY` is configured.
- [ ] `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` match the actual domain.
- [ ] PostgreSQL is the production database; migrations have been applied and a restore has been tested.
- [ ] KYC storage is private, persistent, access-tested, and backed up.
- [ ] Logs do not contain passwords, secrets, or identity-document contents.
- [ ] Admin accounts are restricted and reviewer permissions are checked.
- [ ] `/health/` responds successfully over HTTPS.
- [ ] CI passes, including tests and `check --deploy`.
- [ ] A separate security and legal review has been completed before any real-money functionality is enabled.

## 5. Rollback and incident response

Document who can disable the service, revoke storage credentials, restore PostgreSQL and media backups, and notify affected users if identity documents may have been exposed. Practice the restore and credential-rotation steps before launch.
