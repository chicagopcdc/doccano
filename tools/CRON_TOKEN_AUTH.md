## Auth flow

On every run, the script:

1. `POST /v1/auth/login/` with `DOCCANO_USERNAME` / `DOCCANO_PASSWORD`.
2. Reads the DRF token from the response body: `{"key": "<token>"}`.
   A session cookie is also set but is ignored.
3. Sends `Authorization: Token <key>` on all subsequent requests.

The frontend continues to use session auth. `TokenAuthentication`
is already enabled for `/v1/*` alongside `SessionAuthentication` in
`backend/config/settings/base.py`.

## Token lifetime

DRF tokens don't expire. The same token is returned on every login (`Token.objects.get_or_create`) until it's
explicitly deleted (admin, management command, or `/v1/auth/logout/`).

We re-login on every run instead of caching the token, so only the service
account password needs to be stored.

## Required env vars

- `DOCCANO_URL` (default `http://localhost`)
- `DOCCANO_USERNAME`, `DOCCANO_PASSWORD` — dedicated service account, not a personal login
- `DOCCANO_PROJECT_NAME`

