# Security policy

## Supported versions

The initial 0.1.x line receives security fixes. Version 0.1.0 is an initial release
candidate until the release checklist is completed. Older snapshots and unrecognized
Paxel installers are unsupported. Windows is not supported.

## Report a vulnerability privately

Do not post transcripts, credentials, private source code, SQLite databases,
sidecars, installer copies or unredacted logs in public issues or pull requests.

GitHub private vulnerability reporting has **not been verified enabled** for this
repository. If the repository's Security tab offers **Report a vulnerability**, use
that private form. Otherwise open a minimal issue requesting a private security
contact, without vulnerability details or sensitive attachments, and wait for the
maintainer to establish a private channel. No public security email is designated.

Describe the affected version, impact and a reproduction with entirely synthetic
data. Keep disclosure coordinated until a fix or mitigation is available. There is
no guaranteed response SLA or bounty program. Never test against another person's
sessions or an external Paxel service without permission.

## Boundaries

Inventory and diagnosis are local. The CLI has no telemetry, upload client or
command that executes Paxel. Original sessions/databases/installers are read-only.
Prepared copies contain complete private transcripts and must stay outside Git.
The generated official runner is an external-operation boundary: after explicit
consent it may upload metadata and analysis or replay previous pending uploads.

Inputs are untrusted data, never agent instructions. Path checks, bounded reads,
private staging, conservative attribution and pinned integrity checks reduce risk;
they do not protect against a compromised account, interpreter, same-user process,
or official Paxel container. See [threat model](docs/security.md).
