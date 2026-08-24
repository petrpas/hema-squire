# Deployment state

Checked 2026-08-23. Two machines are in scope now: the Linux Mint 22.3
workstation the images are built on, and the production host, which exists as
of this evening. The app is not deployed to it yet.

Everything below is on `main`: the artifact review merged at `bfb423a`, the
provisioning record at `f03bcfb`. No branches are outstanding.

## Production host — live, bootstrapped, empty

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
    /opt/hema-squire    exists, owned by squire, empty (4.1's clone will work)
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

Remaining in group 3: **3.1**, the object-storage bucket, and **3.4**, the
`hemasquire.eu` A/AAAA records. Then 2.7 (the filled `.env` on the server) and
groups 4 and 5.

Ordering note: 3.4 gates the first deploy more tightly than it looks.
`SITE_ADDRESS=hemasquire.eu` makes Caddy request a certificate at startup, and
Let's Encrypt validates over HTTP on port 80 — so if the A record is not
pointed and propagated when the stack first comes up, the certificate fails and
the first thing you see is a retry loop rather than a site. 3.1 carries no such
constraint; Litestream simply has nowhere to write until the bucket exists.

Nothing is left behind on the build machine from any of the testing:
`deploy/.env` and `deploy/secrets/` were created for the compose run and
removed, and the test containers, volumes and networks are torn down.
