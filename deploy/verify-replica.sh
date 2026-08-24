#!/usr/bin/env bash
# Checks a freshly created replica bucket before Litestream is pointed at it.
#
# Reads the same variables as docker-compose.yml, so run it with deploy/.env:
#   set -a; . deploy/.env; set +a; deploy/verify-replica.sh
#
# It proves four things, in the order that fails most usefully: the credentials
# authenticate, the bucket accepts a write and returns it, the object is NOT
# readable without credentials, and the key cannot see other buckets. The last
# two are the ones a console screenshot cannot tell you.
set -euo pipefail

for v in REPLICA_ENDPOINT REPLICA_BUCKET LITESTREAM_ACCESS_KEY_ID LITESTREAM_SECRET_ACCESS_KEY; do
	[ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
region="${REPLICA_REGION:-auto}"
key="hema-squire/.verify-$(date +%s)"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
printf 'replica reachability probe\n' > "$work/probe"

export AWS_ACCESS_KEY_ID="$LITESTREAM_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LITESTREAM_SECRET_ACCESS_KEY"

# Prefer a local aws CLI; fall back to the official image so this runs on a
# machine that has only a container engine (the build machine has podman and
# no aws, the server has docker and no aws).
if command -v aws >/dev/null 2>&1; then
	probe=$work/probe
	aws() { command aws --endpoint-url "$REPLICA_ENDPOINT" --region "$region" "$@"; }
elif engine=$(command -v podman || command -v docker); then
	probe=/w/probe
	aws() {
		"$engine" run --rm -i \
			-e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY \
			-v "$work:/w:Z" \
			docker.io/amazon/aws-cli:latest \
			--endpoint-url "$REPLICA_ENDPOINT" --region "$region" "$@"
	}
else
	echo "need either the aws CLI or podman/docker" >&2; exit 2
fi

echo "1. credentials authenticate and the bucket is visible"
aws s3api head-bucket --bucket "$REPLICA_BUCKET" >/dev/null
echo "   ok"

echo "2. write, read back, delete"
aws s3 cp "$probe" "s3://$REPLICA_BUCKET/$key" >/dev/null
aws s3 cp "s3://$REPLICA_BUCKET/$key" - | grep -q 'replica reachability probe'
echo "   ok"

echo "3. the object is not public"
url="${REPLICA_ENDPOINT%/}/$REPLICA_BUCKET/$key"
code="$(curl -s -o /dev/null -w '%{http_code}' "$url" || true)"
if [ "$code" = "200" ]; then
	echo "   FAIL: $url served the object without credentials (HTTP 200)" >&2
	aws s3 rm "s3://$REPLICA_BUCKET/$key" >/dev/null || true
	exit 1
fi
echo "   ok (anonymous GET returned $code)"

echo "4. the key is scoped to this bucket only"
if aws s3api list-buckets --query 'Buckets[].Name' --output text 2>/dev/null | tr '\t' '\n' | grep -qvx "$REPLICA_BUCKET"; then
	echo "   WARNING: this key can list buckets other than $REPLICA_BUCKET" >&2
else
	echo "   ok"
fi

aws s3 rm "s3://$REPLICA_BUCKET/$key" >/dev/null
echo "   probe object removed"
echo
echo "replica bucket is ready for Litestream"
