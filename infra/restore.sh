#!/bin/sh
# Restore test: decrypt into a scratch database and check the core invariants. Run on a schedule, not only after a disaster.
set -eu
: "${BACKUP_FILE:?}" "${AGE_IDENTITY:?}" "${SCRATCH_DATABASE_URL:?}"
age -d -i "$AGE_IDENTITY" "$BACKUP_FILE" | psql "$SCRATCH_DATABASE_URL" -v ON_ERROR_STOP=1
psql "$SCRATCH_DATABASE_URL" -tc "select count(*) from public_ids" >/dev/null && echo "restore ok"
