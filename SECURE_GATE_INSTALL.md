# Secure short-link gate

## What changed

New links use this flow:

```text
Telegram file request
  -> opaque database session
  -> shortener
  -> /complete/<session>
  -> browser/cookie challenge
  -> one-time, user-bound grant
  -> /start grant_<token>
  -> file
```

The encoded database-channel message ID is no longer placed in the public
shortener destination. The existing `yu3elk` flow is retained only for
backward compatibility with old links, and now rejects callbacks that have no
matching pending session.

## Files changed

- `config.py`: removes embedded credentials and adds secure-gate settings.
- `database/database.py`: adds `access_sessions` and `access_grants` with
  atomic one-time consumption.
- `plugins/start.py`: creates secure sessions, validates `grant_` links, and
  keeps the existing strike/cooldown accounting.
- `plugins/route.py`: adds the browser completion page and verification API.
- `bot.py`: creates MongoDB TTL indexes for temporary security records.
- `.env.example`: deployment configuration template.

No new Python dependency is required.

## Required environment variables

Set these before deploying:

```text
TG_BOT_TOKEN=...
APP_ID=...
API_HASH=...
DATABASE_URL=mongodb://...
DATABASE_NAME=OnlyFapsFileShareBot
CHANNEL_ID=-100...
OWNER=your_owner_username
OWNER_ID=123456789
BASE_URL=https://your-public-domain.example
BOT_USERNAME=YourBotUsername
PORT=8001
```

`BASE_URL` must be a public HTTPS URL that reaches this bot's aiohttp server.
`BOT_USERNAME` is the username of the same Telegram bot, without `@`.

Configure each shortener with both values:

```text
SHORTLINK_URL=example-shortener.com
SHORTLINK_API=your-provider-key
```

Use `SECURE_GATE_ENABLED=false` only as a temporary rollback switch. New
links then use the legacy `yu3elk` flow.

## Recommended security settings

```text
SECURE_GATE_ENABLED=true
SECURE_SESSION_TTL=1200
SECURE_GRANT_TTL=300
SECURE_CHALLENGE_MIN_SCORE=3
SECURE_BIND_USER=true
BYPASS_PROTECTION_SECONDS=90
```

The grant is bound to the Telegram user who requested the file, expires after
five minutes by default, and is atomically marked used before the file is
served.

## Important deployment action

The original uploaded source contained bot/API/database/shortener secrets as
fallback values in `config.py`. Those defaults have been removed in this
version, but the credentials should still be rotated in Telegram, MongoDB,
and each shortener provider before deployment. Put the replacement values in
deployment secrets/environment variables, not in source control.

This protection blocks direct payload reuse and basic HTTP/browserless
bypassers. No client-side challenge can stop a fully automated browser that
successfully completes every provider step. If the shortener offers a
server-to-server completion webhook or postback, connect that callback to
`complete_access_session` for a stronger provider-confirmed completion signal.
