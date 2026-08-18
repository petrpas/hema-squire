## ADDED Requirements

### Requirement: Single production process
The application SHALL run as exactly one worker process in production. The scheduler runs in-process,
so a second worker means duplicate bank polling and duplicate reminder emails; the worker count is
therefore an invariant fixed in the image, not a deployment-time tuning parameter. Any future
component that polls an external source SHALL inherit this invariant or move out of process.

#### Scenario: Worker count is not configurable at deploy time
- **WHEN** the production container starts
- **THEN** it runs one uvicorn worker, with the count fixed in the image definition rather than an environment variable

### Requirement: Durable, continuously replicated backups with a rehearsed restore
The production database SHALL be continuously replicated to off-host object storage such that data
loss on host failure is bounded by seconds, and SHALL be restorable to a point in time. A restore
SHALL have been performed successfully on a machine other than the production host before the
deployment is considered done, using only material that survives the loss of that host — the
database replica and an off-host copy of the deployment configuration, since a new host cannot boot
without the latter. Replication failure SHALL be detectable: a stalled replica does not affect
serving or host load, so its freshness is monitored directly rather than inferred. The drill SHALL
be re-rehearsed after material stack changes. Backup retention
SHALL be bounded (weeks, not years), so that deletion of personal data propagates out of history
rather than persisting indefinitely in backups.

#### Scenario: Host is lost
- **WHEN** the production host becomes unrecoverable
- **THEN** a new host restores the database from the replica, losing at most seconds of writes

#### Scenario: Replication stops silently
- **WHEN** replication stops while the application continues serving normally
- **THEN** the staleness of the replica raises an alert rather than waiting to be noticed at restore time

#### Scenario: Deleted data ages out
- **WHEN** a registration is deleted and the retention window elapses
- **THEN** no restorable point in time contains the deleted rows

### Requirement: SQLite runs in WAL mode with enforced integrity
The production database SHALL use WAL journaling, and every connection to it SHALL carry a non-zero
busy timeout and foreign-key enforcement. Journal mode is a property of the file and is established
once; the per-connection settings are established on every connection. Concurrent writers SHALL wait rather than fail immediately, and referential
integrity SHALL be enforced at write time — matching the behaviour of the eventual Postgres target,
so that integrity violations surface when written, not when migrated.

#### Scenario: Scheduler writes during a registration burst
- **WHEN** the scheduler commits while registration requests are writing
- **THEN** contending writers wait within the busy timeout and no request fails with a locked-database error

### Requirement: The application refuses to run with development secrets
The application SHALL refuse to start in production when the token-signing key equals the published
development default. Debug mode, set explicitly, is the only exemption.

#### Scenario: Forgotten secret
- **WHEN** the container starts without a production `secret_key` and without debug mode
- **THEN** startup fails with an explanatory error rather than serving forgeable tokens

### Requirement: Authentication endpoints are throttled
Login and signup SHALL be rate-limited per source address. Password verification is deliberately
expensive, which makes an unthrottled login endpoint both a cheap CPU-exhaustion target and a
credential-stuffing surface. Because the application sits behind a reverse proxy, the limit SHALL
be keyed on the originating client address as established by that proxy — not on the proxy's own
address, which would make the limit a single global bucket, and not on a client-supplied header,
which would let a caller choose the bucket it is counted against.

#### Scenario: Credential stuffing
- **WHEN** one address exceeds the login attempt limit within the window
- **THEN** further attempts receive 429 without performing password verification

#### Scenario: One attacker does not lock out everyone else
- **WHEN** one address is being throttled
- **THEN** a request from a different address in the same window is served normally

### Requirement: Production configuration is scoped to the process that needs it
Secrets SHALL be provided per container rather than per host: the token-signing key and mail
credentials reach the application only, and storage credentials reach the replication process only.
A stock reverse proxy terminating TLS has no need of application secrets, and widening its
environment for convenience widens what a single compromised image discloses.

#### Scenario: Reverse proxy is compromised
- **WHEN** the reverse proxy container's environment is read
- **THEN** it contains no token-signing key, mail password, or storage credential

### Requirement: Tenant isolation is held by a test, not by discipline
A parameterized test SHALL sweep console-scoped endpoints as an organizer of a different tournament
and assert refusal. The test SHALL discover endpoints from the application's route table, so that a
newly added console endpoint is covered by existing rather than by remembering. Refusal SHALL mean
an explicit authorization failure, not merely a non-success response: a handler that runs and then
fails to find a resource is indistinguishable from one with no check at all, so "not found" does not
count as refusal.

#### Scenario: New console endpoint
- **WHEN** a console endpoint is added to the API
- **THEN** the isolation test exercises it against a foreign tournament without being edited

#### Scenario: A console check is removed
- **WHEN** an endpoint stops enforcing console access
- **THEN** the isolation test fails for that endpoint, rather than accepting the not-found response the unchecked handler produces

### Requirement: Production email is delivered
Reminder and notification email SHALL be delivered via SMTP in production. The file outbox remains
the development default; the production mailer is selected by the presence of SMTP configuration.

#### Scenario: Payment reminder in production
- **WHEN** the scheduler determines a reminder is due on a production deployment
- **THEN** the message is handed to the configured SMTP endpoint, not serialized to a directory

### Requirement: Closed network perimeter
The production host SHALL accept inbound traffic only on SSH and HTTP/HTTPS, enforced by a firewall
external to the host, so that container port publication cannot widen the perimeter. SSH SHALL be
key-only with root login disabled. The application container SHALL NOT be directly reachable from
the internet; all traffic terminates at the reverse proxy.

#### Scenario: Container publishes a port
- **WHEN** a container inadvertently publishes a port on the host
- **THEN** the external firewall still refuses inbound traffic to it
