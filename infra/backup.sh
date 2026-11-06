#!/bin/sh
# Encrypted PostgreSQL backup. A backup is not reliable until restore.sh has been run against it on a schedule.
set -eu
: "${BACKUP_RECIPIENT:?age recipient public key required}"
pg_dump "$DATABASE_URL" | age -r "$BACKUP_RECIPIENT" > "backup-$(date -u +%Y%m%dT%H%M%SZ).sql.age"
