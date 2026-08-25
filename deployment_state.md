# Deployment state

Checked 2026-08-25. Two machines are in scope: the Linux Mint 22.3 workstation
the images are built on, and the production host — **which is now serving the
site at https://hemasquire.eu.** The first deploy ran on 2026-08-25; see "First
deploy — live" below for what is up and what is deliberately not.

Everything below is on `main`: the artifact review merged at `bfb423a`, the
provisioning record at `f03bcfb`. No branches are outstanding.

**DNS is IPv4-only by decision: publish the A record, never a AAAA.** IPv6 is
not deactivated anywhere — it is simply never advertised, which is what keeps
clients off it. The host speaks IPv6, sshd answers on it, and — contrary to
what this file argued before the deploy — **so does the app**: `docker-proxy`
binds `[::]:80` and `[::]:443` whatever the bridge and ip6tables say. What is
still unknown is whether the Hetzner firewall passes IPv6 at all, and that
uncertainty is now the whole reason to keep the record IPv4-only. Both the
correction and what a AAAA would actually take are under "Docker does answer on
IPv6" below; the superseded reasoning is under "3.4 should publish an A record
only".

This file is public, so host identifiers appear as placeholders:
`<SERVER_IP>`, `<SERVER_IPV6>` and `<INSTANCE_ID>`. The real values are in the
Hetzner console and in `~/.ssh/config` on the build machine, which is where the
`ssh hemasquire` alias resolves them. Keep it that way when editing — the
reasoning here is worth publishing, the coordinates are not.

## Production host — live, bootstrapped, serving

`<SERVER_IP>`, reachable as `ssh hemasquire` (an `~/.ssh/config` alias for
`squire@<SERVER_IP>` using `~/.ssh/hemasquire_deploy`). Root login is
refused by design; `squire` is in `sudo` and `docker`.

Hetzner instance `<INSTANCE_ID>`, availability zone `hel1-dc2` — **Helsinki, not
Falkenstein or Nuremberg** as task 3.2 specifies. Still Hetzner, still the EU,
so nothing in Decision 1 or the data-residency posture changes. 2 vCPU,
3.7 GiB, 38 GB: the CX23 shape. Ubuntu 26.04 LTS.

`cloud-init status: done`, zero errors in its log, and everything the file
promises is present:

    Docker              29.7.2, active; squire reaches the socket
    Compose             v2 plugin v5.5.0 — the same version that validated
                        docker-compose.yml locally (see below)
    unattended-upgrades active
    git                 2.53.0
    /opt/hema-squire    owned by squire; empty at provisioning, now the clone
    listening           :22 only, plus the local DNS stub

sshd reports `passwordauthentication no`, `permitrootlogin no`,
`kbdinteractiveauthentication no`.

### Two things went wrong on the way, both worth remembering

**The first server was created without its user data.** `cloud-init status`
reported `done` over a 0-byte `/var/lib/cloud/instance/user-data.txt` — a
convincing-looking success on a host that had no `squire` user, no Docker and
`passwordauthentication yes`. Hetzner accepts user data only at creation and
offers no way to attach it afterwards, so the machine was destroyed and
recreated. **Check `/var/lib/cloud/instance/user-data.txt` on any new host**
before believing the file ran; `cloud-init status` alone will not tell you.

**The recreate used the pre-review `cloud-init.yaml`.** The working tree was on
`main`, which did not yet carry the fix, so the drop-in landed as
`99-hardening.conf` with the SSH key pasted in by hand. Corrected on the host
afterwards — renamed to `00-hardening.conf`, `sshd -t`, `systemctl reload ssh`,
with `sshd -T` compared either side and a fresh connection opened to confirm
new logins still worked. The repo's copy is now correct, so a future rebuild
gets it right at boot.

Rebuilding reused the same IP but changed the host key; the stale `known_hosts`
entry was removed (the original is at `~/.ssh/known_hosts.old`).

### Firewall — attached and verified from outside

Verified by probing rather than by reading the console back, since the console
shows what was saved and not what is enforced. The evidence is the difference
between a refusal and a silence:

    22          open
    80, 443     RST — the packet reaches the host, nothing is listening yet
    8080, 3306  timeout — dropped before the host
    ICMP        replies, 53–78 ms

Before the rules were attached, 3306 answered RST like everything else. The
timeout is what proves the rule set is live.

The **ICMP rule is kept deliberately**, against task 3.3's "nothing else". Path
MTU Discovery is carried by ICMP type 3 code 4, and dropping it produces the
failure that is hardest to attribute: a connection that establishes and then
stalls on the first large response, only for clients behind a lower-MTU path.
On IPv6 it is worse than a degradation — neighbour discovery rides on ICMPv6.
The security it would buy is nil against Decision 5's threat model, since
scanners find hosts over TCP and 22/80/443 already answer.

## First deploy — live

`app` and `web` are up under `docker compose`, built from `bca17d6` cloned to
`/opt/hema-squire` over HTTPS (the repo is public, so the host holds no deploy
key). `litestream` is **not** started, because 3.1 is deferred — naming the two
services keeps an unconfigurable container from restarting forever and teaching
everyone to ignore a red line in `docker compose ps`.

    app    healthy 5 s after start, no published ports, /secrets read-only
    web    :80 and :443, certificates for both names on first boot
    both   unless-stopped; docker is enabled at boot, so a reboot self-heals

The database is `/data/hema_squire.sqlite` — **not** `/data/squire.db`, a guess
that cost a stray 0-byte file, since `sqlite3.connect` creates whatever it
cannot find. Open it through a `mode=ro`/`mode=rw` URI so a wrong path fails
instead of quietly succeeding. Migrations ran the full chain to head
`b3d1f0a72c45`; `foreign_key_check` is empty, `integrity_check` is `ok`, and
the file is in `wal` mode, which is task 1.1 confirmed in production rather
than in a test. The schema is 24 tables: the 23 the models declare plus
`alembic_version`. That corrects the "26 tables" figure from the local
rehearsal below, which counted something else.

Certificates issued over **`tls-alpn-01`**, not HTTP-01. The ordering note
further down is still right that DNS has to be pointed before first boot, but
port 80 is the fallback path rather than the one that actually ran.

Verified from outside: 200 on the apex, 308 from plain HTTP, 301 from `www`
preserving a deep path and its query, `/api/health` `ok`, `/api/tournaments`
`[]`, and an unknown deep path served the SPA. A signup round-tripped — 201
with a token, that token read `/api/account`, login returned another — and the
probe account was deleted afterwards, so the owner address is still unclaimed
and `fencers` is empty.

The login throttle was confirmed in both directions, which is the part worth
having evidence for: the sixth attempt from one address returned 429 while a
login from a **different** address succeeded inside the same window, so the
bucket is per-client rather than one global bucket keyed on Caddy's container
address. The app logs the caller's real public address, and a forged
`X-Forwarded-For` was still counted against the caller — task 2.4's overwrite
working. One trap: a malformed body answers 422 *before* the limiter runs, so a
probe using a reserved address like `@example.invalid` never reaches the
throttle and looks like a broken limit.

First boot populated the fighters index by itself — 20,339 fighters, refresh
status `ok`, about a minute in — which incidentally proves outbound HTTPS from
the container.

What is deliberately absent: SMTP (no credentials, so `OutboxMailer` records
mail instead of sending it), the Anthropic key (LLM table import), the Google
service-account JSON over an empty `deploy/secrets/` (Sheets export), and the
replica. Each disables a feature; none breaks one.

### The one thing still owed from the deploy

`deploy/.env` exists on the server, `chmod 600`, with the signing key generated
on the host so it never touched the build machine. **It is not in the password
manager yet, and that is the half of task 2.7 that makes it a backup.** Right
now the signing key exists on exactly one disk. Losing the host invalidates
every token ever issued — the part of a restore the replica cannot carry — and
task 5.1's drill stays blocked, because a drill that uses the production host's
own copy proves nothing about recovering from its loss.

    ssh hemasquire cat /opt/hema-squire/deploy/.env

## Docker does answer on IPv6 — the 3.4 reasoning was right by accident

The argument recorded below for publishing no AAAA says a container published
as `80:80` binds IPv4 only, on the evidence of `EnableIPv6: false` and empty
ip6tables DOCKER chains. **That premise is wrong**, and the running stack shows
it: `docker-proxy` listens on `[::]:80` and `[::]:443`, and a request to the
host's own global IPv6 address answered 308 on port 80 and 200 on 443 with the
right certificate. Userland proxying binds a dual-stack wildcard socket no
matter what the bridge and ip6tables do; the ip6tables reasoning governs the
routed path, not the proxy.

The decision does not change, for a reason the original argument never reached:
**whether the Hetzner firewall passes IPv6 at all is still untested.** Its
rules carry explicit source CIDRs, and a rule set written only with `0.0.0.0/0`
drops v6 regardless of what the host does. The test above ran from the host
itself and so never crossed the firewall, and the build machine has no IPv6 to
test from. Publishing a AAAA on that uncertainty risks exactly the failure the
original note feared, so: still A only.

What it changes is the work a AAAA would take. It is no longer "enable IPv6 in
`daemon.json`, pick a CIDR, then verify" — the serving side already works.
It is: check the firewall from a v6-capable vantage point, confirm 80 and 443
answer from off-host, and only then publish the record.

## Build machine — images build, verified

Both stages of `deploy/Dockerfile` were built here and succeeded:

    podman build -f deploy/Dockerfile --target backend -t squire-backend:local .
    podman build -f deploy/Dockerfile --target web     -t squire-web:local     .

Backend 293 MB, web 64 MB. `python:3.14-slim` pulls (matches the backend's
`requires-python = ">=3.14"`), the `COPY --from=ghcr.io/astral-sh/uv:latest`
cross-image copy works, and `uv sync --frozen` resolves against the committed
lockfile.

The engine is **podman 4.9.3**, not Docker. The Dockerfile's fully-qualified
base names are load-bearing here rather than merely tidy: bare `caddy` has no
short-name alias and would not resolve. Rootless is configured correctly —
`petr` has `/etc/subuid` and `/etc/subgid` entries.

## Compose runs on the build machine too

An earlier note concluded the stack could not be brought up locally and that
the server would be the compose file's first run. That was too pessimistic: it
measured `docker compose` (the shim lands on the deprecated Python v1) rather
than `podman-compose` 1.0.6, which is installed and does the job.

    podman-compose -f deploy/docker-compose.yml up -d --build

All three services ran. `app` migrated a fresh volume with alembic and served
uvicorn; `podman inspect` confirms it publishes no ports, mounts `/secrets`
read-only and carries `unless-stopped`, as do the other two. Caddy served the
SPA including the deep-path fallback, and proxied `/api/health` and
`/api/tournaments`. Litestream replicated the real 1.4 MB migrated database to
a MinIO container standing in for the replica bucket.

The compose file was separately validated by the genuine Compose v2 binary
(v5.5.0, extracted from `docker/compose-bin`, no daemon needed):
`docker compose -f deploy/docker-compose.yml config` reports no warnings,
interpolates `deploy/.env` from the project directory as the file's header
claims, resolves `./secrets` relative to `deploy/`, and keeps the healthcheck
as a `CMD` array. The production host runs that same v5.5.0.

Two deviations were needed locally, neither a defect in the file:

1. **Ports.** `net.ipv4.ip_unprivileged_port_start = 1024`, so `80:80` /
   `443:443` cannot bind rootless. Caddy was run on `8080:80` instead.
   podman-compose does not support Compose v2's `!override` tag and appends
   port lists rather than replacing them, so an override file cannot express
   this — the web container was started by hand from the compose-built image.
2. **Healthcheck.** podman-compose flattens the `["CMD", "python", ...]` array
   into a shell string and mangles the quoting, so the container never reports
   healthy (`/bin/sh: 1: Syntax error: word unexpected`). The same command run
   directly in the container exits 0, and Compose v2 keeps the array form.

One trap worth remembering: a failed bind on port 80 tears down the podman
network (`aardvark pid not found`) and leaves already-running containers with
DNS that resolves but addresses that are unreachable — which presents as a 502
from Caddy. Restarting the app container fixes it.

## Backup loop rehearsed end to end

Against a local MinIO, using the committed `deploy/litestream.yml` and
`deploy/restore.sh` unmodified: replicate, then restore with the script's exact
URL and flags. `-integrity-check full` passed and a row written after the
snapshot was present in the restored copy. Repeated against the real migrated
schema from the compose stack — 26 tables, alembic head `b3d1f0a72c45`,
`PRAGMA integrity_check` ok and `PRAGMA foreign_key_check` empty, which is task
4.2 rehearsed early.

This is **not** the restore drill of task 5.1, which is still open: that drill
must run against the production replica using the password-manager copy of
`deploy/.env`, and neither exists yet.

## Two facts about Litestream 0.5.16 that the tasks had wrong

- **`litestream snapshots` does not exist.** It is a 0.3 command. The 0.5
  surface is `ltx`, `status`, `info`, `list`. Tasks 4.3 and 5.2 were corrected.
- **An unreachable endpoint is completely silent.** The daemon logs
  `replicating to …` and then nothing — no error, no exit, the container stays
  up. So the "alert on the container's restart count" fallback suggested in
  task 5.2 would never fire, and monitoring has to look at replica freshness.

Also worth knowing when reading the config: 0.5.16 ignores unknown config keys,
so a clean parse proves nothing about whether a key is honoured. Fields were
probed by giving them an invalid duration — `snapshot.interval`,
`snapshot.retention` and `validation.interval` all fail to unmarshal into
`time.Duration`, so all three are genuinely read.

## Build machine toolchain

Present: node 22.23.2, npm 10.9.8, git 2.43.0, ssh (OpenSSH 9.6p1), openssl,
podman / podman-compose / buildah. 115 GB free on `/`.

Missing: **`uv`**. Irrelevant to image builds — the Dockerfile pulls it from
`ghcr.io` — but needed for local backend development.

## Open

The SSH private key is backed up as of 2026-08-24. `~/.ssh/hemasquire_deploy`
had existed on the build machine and nowhere else, which made it the only way
into a host with password authentication disabled; it is now also in the
password manager. That is where the filled `deploy/.env` belongs too when it
exists — Decision 7's argument applied to the key as well as the database. The
working tree is not a staging area for either: the root `.gitignore` now
carries key and archive patterns so a copy left there cannot be staged by
accident.

Group 3 is closed except **3.1**, the object-storage bucket — **deliberately
deferred on 2026-08-24** for the roughly one-month testing period, so the first
deploy brings up `app` and `web` only. Nothing depends on `litestream`, so the
site is identical without it; what is absent is the safety net. Two things make
that a decision rather than a postponement worth forgetting:

- A test month still accumulates real accounts and a real test tournament, and
  testing periods rarely end with a ceremony that reminds anyone to revisit
  this. Losing the disk during it loses everything written since the deploy.
- Litestream's failure mode is silence (see below), so switching it on later is
  not self-verifying. `deploy/verify-replica.sh` exists to check the bucket
  before Litestream is pointed at it, and task 5.2's freshness alert is what
  proves it stayed working.

Group 4 is done apart from the two checks in 4.3 that the deferrals block —
the SMTP reminder email and the replica being live. What is left is the
password-manager copy of `.env` (the open half of 2.7, above) and group 5,
whose restore drill is blocked on that copy.

**3.4 is done as of 2026-08-24.** `hemasquire.eu` and `www.hemasquire.eu` both
resolve to the server with TTL 300, neither has a AAAA, and four independent
resolvers agree, so it has propagated rather than merely been saved. There is
no CAA record, so nothing constrains which CA may issue. From outside, port 80
answers `connection refused`: the firewall passes the packet and nothing is
listening yet, which is exactly the pre-deploy state — and it is the same
signal that will become a served page once the stack is up.

That consequence is now handled in the Caddyfile: a `www.{$SITE_ADDRESS}` block
redirects to the canonical host with `redir … permanent`, keeping path and
query. Tested against the real Caddy binary rather than reasoned about —
`caddy validate` passes (the only warning is the documented `header_up` lint),
and a container run with `SITE_ADDRESS=localhost`, so nothing touched Let's
Encrypt, answered `301` to `https://localhost/tournaments/abc?x=1&y=2` for the
deep path with query, and `308` from plain HTTP up to HTTPS first.

It is a 301, cached by browsers indefinitely, which is right for a canonical
host but awkward to walk back. It also means Caddy now requests a certificate
for `www.hemasquire.eu` as well, so **the `www` record has to keep resolving**;
removing it without removing this block leaves issuance retrying forever.

Ordering note: 3.4 gates the first deploy more tightly than it looks.
`SITE_ADDRESS=hemasquire.eu` makes Caddy request a certificate at startup, and
Let's Encrypt validates over HTTP on port 80 — so if the A record is not
pointed and propagated when the stack first comes up, the certificate fails and
the first thing you see is a retry loop rather than a site. 3.1 carries no such
constraint; Litestream simply has nowhere to write until the bucket exists.

### 3.4 should publish an A record only — no AAAA

**Superseded in its reasoning, not in its conclusion.** The claim below that a
published container binds IPv4 only was disproved by the running stack — see
"Docker does answer on IPv6" above. The record stays A-only for a different
reason: the firewall's v6 behaviour is untested. The rest of this section is
kept because the Let's Encrypt failure mode it describes is what makes an
unverified AAAA expensive.

The host's IPv6 is real: cloud-init configured `<SERVER_IPV6>/64` on
`eth0`, the default route via `fe80::1` works, outbound reaches the internet
(1.7-7.7 ms to `2606:4700:4700::1111`) and sshd listens on `[::]:22`. So the
usual Hetzner trap — a /64 is routed to the machine but no address is
configured on it — does not apply here.

What does apply is the second half of that warning: whether the *application*
listens on it. Caddy will not. There is no `/etc/docker/daemon.json`, the
default bridge reports `EnableIPv6: false`, and both ip6tables DOCKER chains
are empty (the filter chain has zero references). A container published as
`80:80` therefore binds IPv4 only, and an AAAA record would point at an address
where nothing answers on 80 or 443.

That is worse than having no AAAA at all, and it fails closed in the least
obvious place: Let's Encrypt prefers IPv6 when a AAAA exists, so HTTP-01
validation would be attempted against a dead address and the certificate would
never issue — presenting as exactly the retry loop the ordering note above
describes, while `curl -4` against the same host looks perfect.

So publish the A record and leave AAAA unset. The dual-stack work this
paragraph originally prescribed — `daemon.json` with `"ipv6": true` and
`"ip6tables": true`, a fixed CIDR out of the /64 — turns out not to be needed
for the serving side, which already works; what remains is verifying from a
v6-capable vantage point before the record goes in.

**Untested:** whether the Hetzner firewall passes IPv6 at all. Its rules carry
explicit source CIDRs, so a rule set written only with `0.0.0.0/0` drops v6
regardless of what the host does. The build machine has no IPv6 (no global
address, no default route), so the earlier port probes were IPv4-only and this
could not be checked from here. It needs a v6-capable vantage point — and it
only becomes relevant if dual-stack is pursued.

Nothing is left behind on the build machine from any of the testing:
`deploy/.env` and `deploy/secrets/` were created for the compose run and
removed, and the test containers, volumes and networks are torn down. The
production `.env` was written on the server and has never existed here.
