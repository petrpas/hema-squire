#!/usr/bin/env bash
# Daily proof that the replica keeps up (task 5.2). Runs from cron on the host:
#   17 5 * * * /opt/hema-squire/deploy/check-replica.sh 2>&1 | logger -t check-replica
#
# A dead-man's switch: success pings REPLICA_HEARTBEAT_URL, a detected failure
# pings its /fail, and a host or cron that is gone sends nothing, which the
# monitoring service reports on its own.
#
# It compares positions rather than the age of the newest file, because an idle
# database writes no new files and a quiet day must not look like a stall. The
# local position is read first and the replica after a pause, so a write landing
# in between cannot read as lag.
set -euo pipefail

cd "$(dirname "$0")/.."
db=/data/hema_squire.sqlite
settle="${SETTLE_SECONDS:-30}"

url=$(awk -F= '/^REPLICA_HEARTBEAT_URL=/ {
  sub(/^[^=]*=/, ""); sub(/#.*/, ""); gsub(/[[:space:]]/, ""); print; exit
}' deploy/.env)
[ -n "$url" ] || { echo "REPLICA_HEARTBEAT_URL is empty" >&2; exit 2; }

fail() {
	echo "replica check failed: $1" >&2
	curl -fsS -m 10 --retry 3 -o /dev/null --data-raw "$1" "$url/fail" || true
	exit 1
}

litestream() {
	docker compose -f deploy/docker-compose.yml exec -T litestream litestream "$@"
}

local_json=$(litestream status -json "$db" 2>&1) || fail "litestream is not answering: $local_json"
local_txid=$(python3 -c '
import json, sys
print(json.loads(sys.argv[1])[0]["local_txid"])' "$local_json" 2>/dev/null) ||
	fail "unreadable status: $local_json"

sleep "$settle"

replica_json=$(litestream ltx -level all -json "$db" 2>&1) || fail "replica cannot be listed: $replica_json"
replica_txid=$(python3 -c '
import json, sys
print(max(f["max_txid"] for f in json.loads(sys.argv[1])))' "$replica_json" 2>/dev/null) ||
	fail "replica holds no files: $replica_json"

# Both are fixed-width hex, so string order is numeric order.
if [[ "$replica_txid" < "$local_txid" ]]; then
	fail "replica at $replica_txid, database was at $local_txid"
fi

curl -fsS -m 10 --retry 3 -o /dev/null "$url"
echo "ok: replica at $replica_txid, database was at $local_txid"
