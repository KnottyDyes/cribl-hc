# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[security advisories](https://github.com/KnottyDyes/cribl-hc/security/advisories/new)
rather than opening a public issue.

Include what you did, what happened, and what you expected. A proof of concept
helps but is not required.

## Scope

This tool reads from Cribl deployments and writes nothing back, so the security
surface is mainly the credentials it stores and the data it handles on your
behalf.

Of particular interest:

- The credential store (`cribl_hc/core/credential_store.py`)
- Anything that could write a token, client secret or password into a log,
  report, API response or exception message
- The REST API, which has no authentication of its own (see below)

## What this tool does with credentials

Credentials are stored encrypted with Fernet in `~/.cribl-hc/credentials.enc`,
owner-readable only, and the directory holding them is `0700`. The key comes
from the first of:

1. `CRIBL_HC_MASTER_KEY` — a Fernet key supplied by the environment
2. `CRIBL_HC_MASTER_PASSPHRASE` — derived with PBKDF2-HMAC-SHA256 (600,000
   iterations) over a salt stored beside the data; the passphrase is never
   written to disk
3. A generated key file in the same directory

Option 3 is the default because it needs no setup, and it is worth being plain
about what it buys: the key sits next to the ciphertext, so it protects a stray
backup or a shared filesystem from casual reading, not anyone who can already
read that directory as your user. **Use option 1 or 2 where the distinction
matters** — they are the ones that separate key from data.

## Known limitations

These are design choices rather than defects, listed so you can judge them:

- **The REST API has no authentication.** It is intended for `localhost` use by
  the bundled web UI. Do not expose it to a network you do not control.
- **Analysis reports may contain deployment detail** — hostnames, pipeline
  names, sampled field names — so treat generated reports as you would the
  configuration they describe. See [docs/DATA_PRIVACY.md](docs/DATA_PRIVACY.md).
- **API tokens are held in memory** for the duration of a run, as any HTTP
  client must.

## Supported versions

This project is pre-1.0. Fixes land on `main`; there are no maintained release
branches.
