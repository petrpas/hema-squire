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
# An optional RFC3339 timestamp restores to a point in time. Then the latest
# state is restored as well, only to read its erasure log, and every account
# deleted since that point is erased again before anyone can reach it (spec
# account-deletion, A restore reapplies erasures).
set -euo pipefail

LITESTREAM_IMAGE="${LITESTREAM_IMAGE:-docker.io/litestream/litestream:0.5.16}"
TARGET="${TARGET:-./restored.sqlite}"
TS_ARG=()
[[ $# -ge 1 ]] && TS_ARG=(-timestamp "$1")

REPLICA="s3://${REPLICA_BUCKET}/hema-squire?endpoint=${REPLICA_ENDPOINT}&region=${REPLICA_REGION:-auto}"

restore() {  # restore OUTPUT [litestream options...]
  local output="$1"
  shift
  docker run --rm \
    -e LITESTREAM_ACCESS_KEY_ID -e LITESTREAM_SECRET_ACCESS_KEY \
    -v "$(pwd):/out" \
    "$LITESTREAM_IMAGE" restore \
    -o "/out/${output#./}" \
    -integrity-check full \
    "$@" \
    "$REPLICA"
}

restore "$TARGET" "${TS_ARG[@]}"

if [[ ${#TS_ARG[@]} -gt 0 ]]; then
  LATEST="./latest-for-erasures.sqlite"
  rm -f "$LATEST"
  restore "$LATEST"
  # migrate the restored copy to the current schema, then erase again; in the
  # app image, which carries the code, with this directory mounted as /out
  docker compose -f deploy/docker-compose.yml run --rm --no-deps \
    -e HEMA_SQUIRE_DATABASE_URL="sqlite:////out/${TARGET#./}" \
    -v "$(pwd):/out" -v "$(pwd)/scripts:/scripts:ro" \
    app sh -c "alembic upgrade head && python /scripts/reapply_erasures.py /out/${LATEST#./}"
  rm -f "$LATEST"
fi

echo "Restored to ${TARGET}. Verify: sqlite3 ${TARGET} 'select count(*) from registrations;'"
echo "Real recovery: place it as the app volume's /data/hema_squire.sqlite before first start."
