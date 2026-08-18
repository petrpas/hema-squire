#!/usr/bin/env bash
# Restore the database from the replica into ./restored.sqlite.
# Used for the restore drill (task 5.1) and for real recovery on a new host.
# The image tag must match the one in docker-compose.yml: 0.5 cannot read a
# replica written by 0.3, and vice versa.
#
# Both halves of a recovery come from off-host storage: this script needs the
# replica variables, and the new host needs the rest of deploy/.env — take them
# from the password manager copy, not from the machine you are replacing.
#   set -a; source deploy/.env; set +a; ./deploy/restore.sh [timestamp]
# An optional RFC3339 timestamp restores to a point in time.
set -euo pipefail

LITESTREAM_IMAGE="${LITESTREAM_IMAGE:-docker.io/litestream/litestream:0.5.16}"
TARGET="${TARGET:-./restored.sqlite}"
TS_ARG=()
[[ $# -ge 1 ]] && TS_ARG=(-timestamp "$1")

docker run --rm \
  -e LITESTREAM_ACCESS_KEY_ID -e LITESTREAM_SECRET_ACCESS_KEY \
  -v "$(pwd):/out" \
  "$LITESTREAM_IMAGE" restore \
  -o "/out/${TARGET#./}" \
  -integrity-check full \
  "${TS_ARG[@]}" \
  "s3://${REPLICA_BUCKET}/hema-squire?endpoint=${REPLICA_ENDPOINT}&region=${REPLICA_REGION:-auto}"

echo "Restored to ${TARGET}. Verify: sqlite3 ${TARGET} 'select count(*) from registration;'"
echo "Real recovery: place it as the app volume's /data/hema_squire.sqlite before first start."
