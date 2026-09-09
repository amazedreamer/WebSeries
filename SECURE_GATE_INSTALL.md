# Secure short-link gate

## What changed

The default Telegram-only flow uses this:

```text
Telegram file request
  -> opaque database session
  -> shortener
  -> t.me/<bot>?start=access_<session>
  -> exact token, owner, expiry and time checks
  -> file
```

The encoded database-channel message ID is no longer placed in the public
shortener destination. The final destination is a normal Telegram deep link;
the bot's web `BASE_URL` is not involved. When secure mode is enabled, old
`yu3elk` links are rejected because they expose the file payload and cannot be
upgraded safely.

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
# Leave empty in SECURE_GATE_MODE=telegram.
BASE_URL=
BOT_USERNAME=YourBotUsername
PORT=8001
```

`BOT_USERNAME` is the username of the same Telegram bot, without `@`. The
running bot also stores its username in each new session. `BASE_URL` is not
required in the default Telegram mode. The optional browser mode
(`SECURE_GATE_MODE=web`) still requires a public HTTPS `BASE_URL` and the
Telegram Login Widget domain configuration.

Configure each shortener with both values:

```text
SHORTLINK_URL=example-shortener.com
SHORTLINK_API=your-provider-key
```

Leave `BASE_URL` empty if you use the default Telegram mode. Do not set
`SECURE_GATE_MODE=web` unless users can reach the public web host. After
deployment, all links must be regenerated; old `yu3elk` links are
intentionally invalid.
Use `SECURE_GATE_ENABLED=false` only as a temporary rollback switch. New
links then use the legacy `yu3elk` flow.

## Recommended security settings

```text
SECURE_GATE_ENABLED=true
SECURE_GATE_MODE=telegram
SECURE_SESSION_TTL=1200
SECURE_GRANT_TTL=300
SECURE_CHALLENGE_MIN_SCORE=3
SECURE_BIND_USER=true
BYPASS_PROTECTION_SECONDS=90
```

The opaque session is bound to the Telegram user who requested the file,
expires after 20 minutes by default, and is atomically marked used before the
file is served. A bypass bot that produces a different deep-link payload gets
an invalid-token response. A token returned immediately is also rejected until
`BYPASS_PROTECTION_SECONDS` has elapsed.

## Important deployment action

The original uploaded source contained bot/API/database/shortener secrets as
fallback values in `config.py`. Those defaults have been removed in this
version, but the credentials should still be rotated in Telegram, MongoDB,
and each shortener provider before deployment. Put the replacement values in
deployment secrets/environment variables, not in source control.

This protection blocks direct payload reuse and basic HTTP/browserless
bypassers without requiring users to open `BASE_URL`. It cannot distinguish a
real user from an automated client that obtains the exact final Telegram link
and deliberately waits out the configured delay; a shortener server-to-server
completion webhook would be required for that stronger guarantee.
