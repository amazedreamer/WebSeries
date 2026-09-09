from aiohttp import web
import aiohttp
import secrets
import time
import json
import os
import ipaddress
import hmac
import hashlib
import html
import json
from datetime import datetime
from collections import defaultdict
from database.database import db
from config import (
    BASE_URL,
    BOT_USERNAME,
    LOGGER,
    SHORTLINK_URL,
    SECURE_CHALLENGE_MIN_SCORE,
    SECURE_GRANT_TTL,
    SECURE_SESSION_TTL,
    TG_BOT_TOKEN,
)

routes = web.RouteTableDef()

# ======================== IP RATE LIMITER ======================== #

class RateLimiter:
    """In-memory IP rate limiter. Blocks IPs making too many requests."""
    def __init__(self, max_requests=15, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)  # IP -> [timestamps]
    
    def is_blocked(self, ip: str) -> bool:
        now = time.time()
        # Clean old entries
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]
        # Check limit
        if len(self.requests[ip]) >= self.max_requests:
            return True
        # Record this request
        self.requests[ip].append(now)
        return False
    
    def get_count(self, ip: str) -> int:
        now = time.time()
        return len([t for t in self.requests[ip] if now - t < self.window])


rate_limiter = RateLimiter(max_requests=15, window_seconds=60)


# ======================== GEOIP / VPS DETECTION ======================== #

# Known datacenter/VPS IP ranges (CIDR notation)
# Sources: AWS, DigitalOcean, Google Cloud, Hetzner, OVH, Vultr, Linode
VPS_CIDR_RANGES = [
    # AWS (precise ranges — NOT broad /8 blocks)
    "3.0.0.0/15", "3.2.0.0/16", "3.4.0.0/14", "3.8.0.0/13",
    "3.16.0.0/12", "3.32.0.0/11", "3.64.0.0/10", "3.128.0.0/9",
    "13.32.0.0/11", "13.52.0.0/14", "13.56.0.0/14",
    "13.112.0.0/12", "13.208.0.0/12", "13.224.0.0/11",
    "18.128.0.0/9", "18.64.0.0/10", "18.32.0.0/11",
    "34.192.0.0/10", "34.128.0.0/10",
    "35.72.0.0/13", "35.80.0.0/12", "35.152.0.0/13",
    "35.160.0.0/11",
    "52.0.0.0/11", "52.32.0.0/11", "52.64.0.0/12",
    "52.80.0.0/13", "52.92.0.0/14", "52.192.0.0/11",
    "52.224.0.0/11",
    "54.64.0.0/11", "54.144.0.0/12", "54.160.0.0/11",
    "54.192.0.0/12", "54.208.0.0/13", "54.216.0.0/14",
    "54.224.0.0/12", "54.240.0.0/12",
    # DigitalOcean
    "104.131.0.0/16", "104.236.0.0/16", "138.68.0.0/16",
    "139.59.0.0/16", "142.93.0.0/16", "157.230.0.0/16",
    "159.65.0.0/16", "159.89.0.0/16", "161.35.0.0/16",
    "164.90.0.0/16", "165.22.0.0/16", "167.71.0.0/16",
    "167.172.0.0/16", "174.138.0.0/16", "178.128.0.0/16",
    "188.166.0.0/16", "206.189.0.0/16", "209.97.0.0/16",
    # Google Cloud
    "34.64.0.0/10", "35.184.0.0/13", "35.192.0.0/12",
    "35.208.0.0/12", "35.224.0.0/12", "35.240.0.0/13",
    # Hetzner
    "5.9.0.0/16", "78.46.0.0/15", "88.99.0.0/16",
    "94.130.0.0/16", "95.216.0.0/16", "116.202.0.0/16",
    "116.203.0.0/16", "135.181.0.0/16", "136.243.0.0/16",
    "138.201.0.0/16", "144.76.0.0/16", "148.251.0.0/16",
    "159.69.0.0/16", "176.9.0.0/16", "178.63.0.0/16",
    "188.40.0.0/16", "195.201.0.0/16", "213.133.0.0/16",
    "213.239.0.0/16",
    # OVH
    "51.38.0.0/16", "51.68.0.0/16", "51.75.0.0/16",
    "51.77.0.0/16", "51.79.0.0/16", "51.81.0.0/16",
    "51.83.0.0/16", "51.89.0.0/16", "51.91.0.0/16",
    "51.161.0.0/16", "51.178.0.0/16", "51.195.0.0/16",
    "51.210.0.0/16", "51.222.0.0/16", "54.36.0.0/16",
    "54.37.0.0/16", "54.38.0.0/16", "87.98.0.0/16",
    "91.121.0.0/16", "92.222.0.0/16", "137.74.0.0/16",
    "145.239.0.0/16", "149.202.0.0/16", "151.80.0.0/16",
    "164.132.0.0/16", "176.31.0.0/16", "178.32.0.0/16",
    "178.33.0.0/16", "188.165.0.0/16", "193.70.0.0/16",
    "198.27.0.0/16", "198.50.0.0/16", "198.100.0.0/16",
    # Vultr
    "45.32.0.0/16", "45.63.0.0/16", "45.76.0.0/16",
    "45.77.0.0/16", "64.156.0.0/16", "66.42.0.0/16",
    "78.141.0.0/16", "95.179.0.0/16", "104.207.0.0/16",
    "104.238.0.0/16", "108.61.0.0/16", "136.244.0.0/16",
    "140.82.0.0/16", "141.164.0.0/16", "149.28.0.0/16",
    "155.138.0.0/16", "207.246.0.0/16", "209.250.0.0/16",
    "216.128.0.0/16", "217.69.0.0/16",
    # Linode
    "45.33.0.0/16", "45.56.0.0/16", "45.79.0.0/16",
    "50.116.0.0/16", "66.175.0.0/16", "69.164.0.0/16",
    "72.14.0.0/16", "74.207.0.0/16", "96.126.0.0/16",
    "97.107.0.0/16", "139.144.0.0/16", "139.162.0.0/16",
    "170.187.0.0/16", "172.104.0.0/16", "172.105.0.0/16",
    "173.230.0.0/16", "173.255.0.0/16", "178.79.0.0/16",
    "194.195.0.0/16", "198.58.0.0/16",
    # Azure (precise — NOT broad /8)
    "13.64.0.0/11", "20.33.0.0/16", "20.34.0.0/15",
    "20.36.0.0/14", "20.40.0.0/13", "20.48.0.0/12",
    "20.64.0.0/10", "20.128.0.0/16", "20.150.0.0/15",
    "20.184.0.0/13", "20.192.0.0/10",
    "40.64.0.0/10", "40.128.0.0/12",
    "51.104.0.0/15", "52.224.0.0/11",
]

# Pre-parse CIDR ranges into network objects for fast lookup
_vps_networks = []
for cidr in VPS_CIDR_RANGES:
    try:
        _vps_networks.append(ipaddress.ip_network(cidr, strict=False))
    except ValueError:
        pass


def is_vps_ip(ip_str: str) -> bool:
    """Check if an IP belongs to a known VPS/datacenter."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.version == 6:
            return False
        for network in _vps_networks:
            if ip in network:
                return True
        return False
    except Exception:
        return False


# ======================== IP LOGGER ======================== #

IP_LOG_FILE = "ip_logs.txt"

def log_ip(ip: str, hash_id: str, user_agent: str, status: str):
    """Log visitor IP to ip_logs.txt."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] IP={ip} | Link={hash_id[:20]}... | Status={status} | UA={user_agent[:80]}\n"
        with open(IP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        LOGGER(__name__).error(f"IP log write error: {e}")


# ======================== HELPER: GET CLIENT IP ======================== #

def get_client_ip(request) -> str:
    """Get the real client IP, accounting for proxies."""
    # Check common proxy headers
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            # Use the last IP in X-Forwarded-For to prevent spoofing
            return ips[-1]
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    # Fallback to direct connection
    peername = request.transport.get_extra_info('peername')
    if peername:
        return peername[0]
    return "unknown"


# ======================== ROUTES ======================== #

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Codeflix FileStore")


# ======================== SERVER-SIDE COMPLETION GATE ====================== #

def _verify_telegram_login(user_data: dict) -> bool:
    """
    Verify Telegram Login Widget data using the bot token.

    This is the important anti-bypass step: a shortener scraper can fetch a
    page, but it cannot manufacture a valid Telegram-signed user payload for
    the account that requested the file.
    """
    if not TG_BOT_TOKEN or not isinstance(user_data, dict):
        return False

    supplied_hash = str(user_data.get("hash", ""))
    raw_id = user_data.get("id")
    raw_auth_date = user_data.get("auth_date")
    if not supplied_hash or not raw_id or not raw_auth_date:
        return False

    try:
        auth_date = int(raw_auth_date)
        user_id = int(raw_id)
    except (TypeError, ValueError):
        return False

    now = int(time.time())
    if auth_date > now + 60 or now - auth_date > 86400:
        return False

    fields = []
    for key in sorted(user_data):
        if key == "hash" or user_data[key] is None:
            continue
        fields.append(f"{key}={user_data[key]}")
    data_check_string = "\n".join(fields)
    secret_key = hashlib.sha256(TG_BOT_TOKEN.encode("utf-8")).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return user_id > 0 and hmac.compare_digest(expected_hash, supplied_hash)


@routes.get("/complete/{session_token}")
async def secure_completion_page(request):
    """
    Destination used by new shortener links.

    It deliberately does not expose the file payload.  A browser must retain
    the session cookie and pass the lightweight challenge before the server
    issues a one-time Telegram grant.
    """
    raw_session = request.match_info.get("session_token", "")
    if not raw_session or len(raw_session) > 128:
        return web.Response(text="Invalid verification session.", status=400)

    if not BASE_URL:
        LOGGER(__name__).error(
            "Secure gate requires BASE_URL or RENDER_EXTERNAL_URL to be configured."
        )
        return web.Response(text="Secure gate is not configured.", status=503)

    session_doc = await db.get_access_session(raw_session)
    if not session_doc:
        return web.Response(
            text="This verification link is expired or has already been used.",
            status=410,
        )

    widget_bot = str(
        session_doc.get("bot_username") or BOT_USERNAME
    ).lstrip("@")
    if not widget_bot:
        return web.Response(text="Bot username is not configured.", status=503)

    verify_url = f"{BASE_URL.rstrip('/')}/complete/verify"
    token_js = json.dumps(raw_session)
    widget_bot_html = html.escape(widget_bot, quote=True)
    html_content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Security verification</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center;
      background:#0b0d10; color:#fff; font-family:system-ui,sans-serif; }}
    .card {{ width:min(390px,calc(100% - 40px)); padding:32px; text-align:center;
      background:#15191f; border:1px solid #29313a; border-radius:18px;
      box-shadow:0 16px 50px #0008; }}
    .icon {{ font-size:48px; }}
    h2 {{ margin:12px 0 8px; }}
    p {{ color:#aab4bf; line-height:1.5; }}
    .bar {{ height:5px; margin:22px 0; background:#29313a; border-radius:5px; overflow:hidden; }}
    #fill {{ width:0; height:100%; background:#42e695; transition:width .35s; }}
    #error {{ display:none; color:#ff7777; }}
    small {{ color:#687582; }}
  </style>
</head>
<body>
  <main class="card">
    <div class="icon">🛡️</div>
    <h2>Human verification</h2>
    <p id="status">Complete the short-link steps, then verify with Telegram.</p>
    <div class="bar"><div id="fill"></div></div>
    <div id="telegram-login">
      <script async src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="{widget_bot_html}" data-size="large"
        data-request-access="write"
        data-onauth="onTelegramAuth(user)"></script>
    </div>
    <p id="error"></p>
    <small>Telegram verification binds this link to the requesting account.</small>
  </main>
<script>
let secureFingerprint = null;
let secureScore = 0;
let secureStarted = performance.now();
const secureSession = {token_js};
const secureVerifyUrl = {json.dumps(verify_url)};
const secureMinScore = {int(SECURE_CHALLENGE_MIN_SCORE)};

function onTelegramAuth(telegramUser) {{
  if (!secureFingerprint) {{
    document.getElementById("error").textContent = "Browser verification is still running.";
    document.getElementById("error").style.display = "block";
    return;
  }}
  document.getElementById("status").textContent = "Finalizing secure access...";
  fetch(secureVerifyUrl, {{
    method: "POST",
    credentials: "same-origin",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{
      session: secureSession,
      score: secureScore,
      elapsed_ms: Math.round(performance.now() - secureStarted),
      fingerprint: secureFingerprint,
      telegram: telegramUser
    }})
  }}).then(async function (response) {{
    const data = await response.json();
    if (!response.ok || !data.redirect) throw new Error(data.error || "Verification failed");
    window.location.replace(data.redirect);
  }}).catch(function (e) {{
    document.getElementById("status").textContent = "Verification failed";
    const error = document.getElementById("error");
    error.textContent = e.message || "Please request a new link.";
    error.style.display = "block";
  }});
}}

(function () {{
  const started = performance.now();
  const fill = document.getElementById("fill");
  const status = document.getElementById("status");
  const fp = {{
    webdriver: navigator.webdriver === true,
    plugins: navigator.plugins ? navigator.plugins.length : 0,
    chrome: !!window.chrome,
    screen: (screen.width || 0) + "x" + (screen.height || 0),
    colorDepth: screen.colorDepth || 0,
    language: navigator.language || "",
    platform: navigator.platform || "",
    touchPoints: navigator.maxTouchPoints || 0,
    cookieEnabled: navigator.cookieEnabled === true
  }};
  let score = 0;
  if (!fp.webdriver) score++;
  if (fp.screen !== "0x0") score++;
  if (fp.colorDepth > 0) score++;
  if (fp.cookieEnabled) score++;
  if (fp.plugins > 0 || fp.chrome) score++;
  fill.style.width = Math.min(100, score * 20) + "%";
  secureFingerprint = fp;
  secureScore = score;
  secureStarted = started;
  if (score < secureMinScore) {{
    status.textContent = "Browser verification failed.";
    const error = document.getElementById("error");
    error.textContent = "Please use a normal browser and try again.";
    error.style.display = "block";
  }} else {{
    status.textContent = "Browser checked. Click the Telegram button to continue.";
  }}
}})();
</script>
</body>
</html>"""
    response = web.Response(text=html_content, content_type="text/html")
    response.set_cookie(
        "sg_session",
        raw_session,
        max_age=max(60, int(SECURE_SESSION_TTL)),
        httponly=False,
        samesite="Lax",
        secure=BASE_URL.lower().startswith("https://"),
    )
    return response


@routes.post("/complete/verify")
async def complete_secure_session(request):
    """Turn a browser session plus Telegram Login proof into one grant."""
    try:
        data = await request.json()
        raw_session = str(data.get("session", ""))
        cookie_session = request.cookies.get("sg_session", "")
        score = max(0, min(10, int(data.get("score", 0))))
        elapsed_ms = int(data.get("elapsed_ms", 0))
        fingerprint = data.get("fingerprint") or {}
        telegram = data.get("telegram") or {}
    except (ValueError, TypeError, json.JSONDecodeError):
        return web.json_response({"error": "Invalid verification request."}, status=400)

    if (
        not raw_session
        or not cookie_session
        or not hmac.compare_digest(raw_session, cookie_session)
    ):
        return web.json_response({"error": "Verification session mismatch."}, status=403)

    if fingerprint.get("webdriver") is True:
        return web.json_response({"error": "Automated browser detected."}, status=403)
    if elapsed_ms < 1200 or score < SECURE_CHALLENGE_MIN_SCORE:
        return web.json_response({"error": "Browser verification failed."}, status=403)

    if not _verify_telegram_login(telegram):
        return web.json_response(
            {"error": "Telegram account verification failed."},
            status=403,
        )

    grant = await db.complete_access_session(
        raw_session=raw_session,
        user_agent=request.headers.get("User-Agent", ""),
        client_ip=get_client_ip(request),
        score=score,
        grant_ttl_seconds=SECURE_GRANT_TTL,
        telegram_user_id=int(telegram.get("id", 0)),
    )
    if not grant:
        return web.json_response(
            {"error": "This verification link is expired or already used."},
            status=410,
        )

    bot_username = str(grant.get("bot_username") or BOT_USERNAME).lstrip("@")
    if not bot_username:
        return web.json_response(
            {"error": "Bot username is not configured."},
            status=503,
        )

    return web.json_response({
        "redirect": f"https://t.me/{bot_username}?start=grant_{grant['token']}"
    })


# ======================== MASKED LINK HANDLER ======================== #

@routes.get("/r/{hash_id:.*}", allow_head=True)
async def proxy_request(request):
    hash_id = request.match_info['hash_id']
    user_agent = request.headers.get("User-Agent", "").lower()
    client_ip = get_client_ip(request)
    
    # ─── SECURITY EXCEPTION: Shortener Bypass ───
    # If the user is returning from our configured shortlink URL, bypass the IP block.
    # We check the referer to see if they came from there.
    referer = request.headers.get("Referer", "").lower()
    shortlink_domain = getattr(SHORTLINK_URL, "lower", lambda: str(SHORTLINK_URL).lower())()
    is_shortener_return = shortlink_domain in referer or "arolinks.com" in referer

    # ─── SECURITY LAYER 1: IP Rate Limiting ───
    if not is_shortener_return and rate_limiter.is_blocked(client_ip):
        log_ip(client_ip, hash_id, user_agent, "RATE_LIMITED")
        return _rate_limited_page()

    # ─── SECURITY LAYER 2: VPS/Datacenter IP Blocking ───
    if not is_shortener_return and is_vps_ip(client_ip):
        log_ip(client_ip, hash_id, user_agent, "VPS_BLOCKED")
        return _vps_blocked_page()

    # ─── SECURITY LAYER 3: Check if link is expired (one-time) ───
    base_id = hash_id.split('/')[0]
    entry = await db.get_masked_link(base_id)
    if entry and entry.get("used", False):
        log_ip(client_ip, hash_id, user_agent, "LINK_EXPIRED")
        return _link_expired_page()

    # Log the IP visit
    log_ip(client_ip, hash_id, user_agent, "VISIT")

    # 1. Force Chrome for Telegram Users
    if "telegram" in user_agent:
        base = BASE_URL.rstrip('/')
        current_url = f"{base}{request.path_qs}"
        url_no_scheme = current_url.replace("https://", "").replace("http://", "")
        intent_uri = f"intent://{url_no_scheme}#Intent;scheme=https;package=com.android.chrome;end"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Open in Chrome | Codeflix</title>
            <style>
                :root {{ --primary: #00ff88; --bg: #0a0a0a; --card: #151515; }}
                body {{ background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                .card {{ text-align: center; background: var(--card); padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #222; max-width: 350px; }}
                .btn {{ background: var(--primary); color: #000; padding: 14px 28px; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block; margin-top: 20px; }}
                .icon {{ font-size: 48px; margin-bottom: 15px; }}
                .footer {{ margin-top: 20px; font-size: 0.8em; color: #888; }}
                .brand {{ color: var(--primary); font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">🌐</div>
                <h2>Open in Chrome</h2>
                <p style="color:#888">This link requires Google Chrome.</p>
                <a href="{intent_uri}" class="btn">Open in Chrome</a>
                <div class="footer">Made by <span class="brand">Codeflix</span></div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')

    # 2. Check for confirmed token (after fingerprint verification)
    confirmed_token = request.query.get("confirmed")
    if confirmed_token and confirmed_token != "1":
        # Validate the fingerprint token
        is_valid = await db.validate_fp_token(confirmed_token, base_id)
        if is_valid:
            log_ip(client_ip, hash_id, user_agent, "VERIFIED_PASS")
            # ─── ONE-TIME LINK: Mark as used after successful visit ───
            await db.mark_link_used(base_id)
            return await _proxy_content(request, hash_id)
        else:
            log_ip(client_ip, hash_id, user_agent, "INVALID_TOKEN")
            return _bot_detected_page()

    # 3. Show loading page with device fingerprinting
    base = BASE_URL.rstrip('/')
    verify_url = f"{base}/verify"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Security Check | Codeflix</title>
        <style>
            :root {{
                --primary: #00ff88;
                --bg: #0a0a0a;
                --card: #151515;
                --text: #ffffff;
                --subtext: #888888;
                --danger: #ff4444;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: var(--bg);
                color: var(--text);
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                overflow: hidden;
            }}
            .container {{
                text-align: center;
                background: var(--card);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0, 255, 136, 0.05), 0 10px 30px rgba(0,0,0,0.5);
                border: 1px solid #222;
                max-width: 90%;
                width: 380px;
                position: relative;
                overflow: hidden;
            }}
            .container::before {{
                content: '';
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 4px;
                background: linear-gradient(90deg, transparent, var(--primary), transparent);
                animation: scan 2s linear infinite;
            }}
            @keyframes scan {{
                0% {{ transform: translateX(-100%); }}
                100% {{ transform: translateX(100%); }}
            }}
            .shield {{ font-size: 48px; margin-bottom: 15px; }}
            h2 {{ font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px; }}
            .status {{ color: var(--subtext); font-size: 0.9em; margin-bottom: 20px; }}
            .progress-bar {{
                width: 100%;
                height: 6px;
                background: rgba(255,255,255,0.1);
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 20px;
            }}
            .progress-fill {{
                height: 100%;
                width: 0%;
                background: linear-gradient(90deg, var(--primary), #00cc66);
                border-radius: 3px;
                transition: width 0.3s ease;
            }}
            .checks {{
                text-align: left;
                margin: 15px 0;
                font-size: 0.85em;
            }}
            .check-item {{
                display: flex;
                align-items: center;
                padding: 6px 0;
                color: var(--subtext);
                transition: color 0.3s;
            }}
            .check-item.pass {{ color: var(--primary); }}
            .check-item.fail {{ color: var(--danger); }}
            .check-icon {{ width: 20px; margin-right: 8px; text-align: center; }}
            .footer {{ margin-top: 20px; font-size: 0.75em; color: #555; }}
            .brand {{ color: var(--primary); font-weight: bold; }}
            .error-box {{
                display: none;
                background: rgba(255,68,68,0.1);
                border: 1px solid var(--danger);
                border-radius: 10px;
                padding: 15px;
                margin-top: 15px;
            }}
            .error-box h3 {{ color: var(--danger); margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="shield">🛡️</div>
            <h2>Security Verification</h2>
            <p class="status" id="statusText">Checking device authenticity...</p>

            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>

            <div class="checks">
                <div class="check-item" id="check1">
                    <span class="check-icon">⏳</span>
                    <span>Browser Environment</span>
                </div>
                <div class="check-item" id="check2">
                    <span class="check-icon">⏳</span>
                    <span>WebDriver Detection</span>
                </div>
                <div class="check-item" id="check3">
                    <span class="check-icon">⏳</span>
                    <span>Canvas Fingerprint</span>
                </div>
                <div class="check-item" id="check4">
                    <span class="check-icon">⏳</span>
                    <span>Device Certificate</span>
                </div>
                <div class="check-item" id="check5">
                    <span class="check-icon">⏳</span>
                    <span>Human Interaction</span>
                </div>
            </div>

            <div class="error-box" id="errorBox">
                <h3>⚠️ Bot Detected</h3>
                <p style="color:#888;font-size:0.85em">Automated access is not allowed. Please use a real browser.</p>
            </div>

            <div class="footer">
                Powered by <span class="brand">Codeflix</span> Security
            </div>
        </div>

        <script>
        (function() {{
            var fp = {{}};
            var score = 0;
            var maxScore = 5;
            var hashId = "{hash_id}";
            var verifyUrl = "{verify_url}";

            function setCheck(id, pass) {{
                var el = document.getElementById(id);
                el.classList.add(pass ? 'pass' : 'fail');
                el.querySelector('.check-icon').textContent = pass ? '✅' : '❌';
                if (pass) score++;
                updateProgress();
            }}

            function updateProgress() {{
                var pct = Math.round((score / maxScore) * 100);
                document.getElementById('progressBar').style.width = pct + '%';
            }}

            setTimeout(function() {{
                var hasPlugins = navigator.plugins && navigator.plugins.length > 0;
                var hasChrome = !!window.chrome;
                var hasMime = navigator.mimeTypes && navigator.mimeTypes.length > 0;
                var pass1 = hasPlugins || hasChrome || hasMime;
                fp.plugins = navigator.plugins ? navigator.plugins.length : 0;
                fp.chrome = !!window.chrome;
                fp.platform = navigator.platform;
                fp.language = navigator.language;
                setCheck('check1', pass1);
                document.getElementById('statusText').textContent = 'Scanning WebDriver...';
            }}, 400);

            setTimeout(function() {{
                var isWebdriver = navigator.webdriver === true;
                var hasAutomate = !!document.querySelector('[driver]');
                var pass2 = !isWebdriver && !hasAutomate;
                fp.webdriver = isWebdriver;
                setCheck('check2', pass2);
                document.getElementById('statusText').textContent = 'Generating canvas fingerprint...';
            }}, 900);

            setTimeout(function() {{
                var pass3 = false;
                try {{
                    var canvas = document.createElement('canvas');
                    var ctx = canvas.getContext('2d');
                    ctx.textBaseline = 'top';
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#f60';
                    ctx.fillRect(125, 1, 62, 20);
                    ctx.fillStyle = '#069';
                    ctx.fillText('Codeflix:FP', 2, 15);
                    ctx.fillStyle = 'rgba(102,204,0,0.7)';
                    ctx.fillText('Codeflix:FP', 4, 17);
                    var data = canvas.toDataURL();
                    fp.canvas = data.substring(0, 100);
                    pass3 = data.length > 100;
                }} catch(e) {{
                    fp.canvas = 'error';
                }}
                setCheck('check3', pass3);
                document.getElementById('statusText').textContent = 'Verifying device certificate...';
            }}, 1400);

            setTimeout(function() {{
                var w = screen.width || 0;
                var h = screen.height || 0;
                var hasScreen = w > 0 && h > 0;
                var colorDepth = screen.colorDepth || 0;
                fp.screen = w + 'x' + h;
                fp.colorDepth = colorDepth;
                fp.touchPoints = navigator.maxTouchPoints || 0;
                fp.hardwareConcurrency = navigator.hardwareConcurrency || 0;
                fp.deviceMemory = navigator.deviceMemory || 0;
                try {{
                    var c = document.createElement('canvas');
                    var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
                    if (gl) {{
                        var dbg = gl.getExtension('WEBGL_debug_renderer_info');
                        if (dbg) {{ fp.gpu = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL); }}
                    }}
                }} catch(e) {{ fp.gpu = 'none'; }}
                var pass4 = hasScreen && colorDepth > 0;
                setCheck('check4', pass4);
                document.getElementById('statusText').textContent = 'Finalizing verification...';
            }}, 1900);

            setTimeout(function() {{
                fp.timing = performance.now();
                fp.doNotTrack = navigator.doNotTrack;
                fp.cookieEnabled = navigator.cookieEnabled;
                fp.userAgent = navigator.userAgent;
                var pass5 = fp.timing > 1500;
                setCheck('check5', pass5);
                if (score >= 3) {{
                    document.getElementById('statusText').textContent = 'Verification passed! Redirecting...';
                    submitFingerprint();
                }} else {{
                    document.getElementById('statusText').textContent = 'Verification failed.';
                    document.getElementById('errorBox').style.display = 'block';
                }}
            }}, 2500);

            function submitFingerprint() {{
                var xhr = new XMLHttpRequest();
                xhr.open('POST', verifyUrl, true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function() {{
                    if (xhr.status === 200) {{
                        var resp = JSON.parse(xhr.responseText);
                        if (resp.token) {{
                            var base = window.location.origin;
                            window.location.href = base + '/r/' + hashId + '?confirmed=' + resp.token;
                        }} else {{
                            document.getElementById('statusText').textContent = 'Verification failed.';
                            document.getElementById('errorBox').style.display = 'block';
                        }}
                    }} else {{
                        document.getElementById('statusText').textContent = 'Server error.';
                        document.getElementById('errorBox').style.display = 'block';
                    }}
                }};
                xhr.onerror = function() {{
                    document.getElementById('statusText').textContent = 'Network error.';
                }};
                xhr.send(JSON.stringify({{
                    hash_id: hashId,
                    fingerprint: fp,
                    score: score
                }}));
            }}
        }})();
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')


# ======================== FINGERPRINT VERIFICATION ======================== #

@routes.post("/verify")
async def verify_fingerprint(request):
    """Verify device fingerprint and issue a one-time redirect token."""
    client_ip = get_client_ip(request)
    
    try:
        data = await request.json()
        hash_id = data.get("hash_id", "")
        fingerprint = data.get("fingerprint", {})
        score = data.get("score", 0)

        if not hash_id:
            return web.json_response({"error": "Missing hash_id"}, status=400)

        base_id = hash_id.split('/')[0]
        entry = await db.get_masked_link(base_id)
        if not entry:
            return web.json_response({"error": "Link not found"}, status=404)

        # Anti-bot scoring
        bot_detected = False
        
        if fingerprint.get("webdriver", False):
            bot_detected = True
        
        screen = fingerprint.get("screen", "0x0")
        if screen == "0x0":
            bot_detected = True

        if score < 2:
            bot_detected = True

        if bot_detected:
            log_ip(client_ip, hash_id, str(fingerprint.get("userAgent", "")), "BOT_DETECTED")
            return web.json_response({"error": "Bot detected"}, status=403)

        # Generate a one-time token (valid for 60 seconds)
        token = secrets.token_urlsafe(32)
        expires = time.time() + 60
        await db.store_fp_token(token, base_id, expires)

        return web.json_response({"token": token})

    except Exception as e:
        LOGGER(__name__).error(f"Verify error: {e}")
        return web.json_response({"error": "Server error"}, status=500)


# ======================== PROXY HANDLER ======================== #

async def _proxy_content(request, hash_id):
    """Redirect to the target URL instead of proxying content."""
    base_id = hash_id.split('/')[0]
    entry = await db.get_masked_link(base_id)

    if not entry:
        return web.Response(text="Link not found or has been removed.", status=404)

    target_url = entry["target"]
    raise web.HTTPFound(target_url)


# ======================== ERROR PAGES ======================== #

def _bot_detected_page():
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied | Codeflix</title>
    <style>
        body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { text-align: center; background: #151515; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #333; max-width: 380px; }
        .icon { font-size: 64px; margin-bottom: 15px; }
        h2 { color: #ff4444; margin-bottom: 10px; }
        p { color: #888; font-size: 0.9em; line-height: 1.6; }
        .footer { margin-top: 25px; font-size: 0.75em; color: #555; }
        .brand { color: #00ff88; font-weight: bold; }
    </style></head>
    <body><div class="card">
        <div class="icon">🤖</div>
        <h2>Bot Detected</h2>
        <p>Automated access is not permitted.<br>Please use a real browser.</p>
        <div class="footer">Protected by <span class="brand">Codeflix</span> Security</div>
    </div></body></html>
    """
    return web.Response(text=html, content_type='text/html', status=200)


def _rate_limited_page():
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rate Limited | Codeflix</title>
    <style>
        body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { text-align: center; background: #151515; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #333; max-width: 380px; }
        .icon { font-size: 64px; margin-bottom: 15px; }
        h2 { color: #ff9900; margin-bottom: 10px; }
        p { color: #888; font-size: 0.9em; line-height: 1.6; }
        .footer { margin-top: 25px; font-size: 0.75em; color: #555; }
        .brand { color: #00ff88; font-weight: bold; }
    </style></head>
    <body><div class="card">
        <div class="icon">⚡</div>
        <h2>Too Many Requests</h2>
        <p>You are making too many requests.<br>Please wait a minute and try again.</p>
        <div class="footer">Protected by <span class="brand">Codeflix</span> Security</div>
    </div></body></html>
    """
    return web.Response(text=html, content_type='text/html', status=200)


def _vps_blocked_page():
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied | Codeflix</title>
    <style>
        body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { text-align: center; background: #151515; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #333; max-width: 380px; }
        .icon { font-size: 64px; margin-bottom: 15px; }
        h2 { color: #ff4444; margin-bottom: 10px; }
        p { color: #888; font-size: 0.9em; line-height: 1.6; }
        .footer { margin-top: 25px; font-size: 0.75em; color: #555; }
        .brand { color: #00ff88; font-weight: bold; }
    </style></head>
    <body><div class="card">
        <div class="icon">🖥️</div>
        <h2>VPS/Server Access Blocked</h2>
        <p>Access from datacenter/VPS IPs is not allowed.<br>Please use a personal device and network.</p>
        <div class="footer">Protected by <span class="brand">Codeflix</span> Security</div>
    </div></body></html>
    """
    return web.Response(text=html, content_type='text/html', status=200)


def _link_expired_page():
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Expired | Codeflix</title>
    <style>
        body { background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { text-align: center; background: #151515; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #333; max-width: 380px; }
        .icon { font-size: 64px; margin-bottom: 15px; }
        h2 { color: #ff4444; margin-bottom: 10px; }
        p { color: #888; font-size: 0.9em; line-height: 1.6; }
        .footer { margin-top: 25px; font-size: 0.75em; color: #555; }
        .brand { color: #00ff88; font-weight: bold; }
    </style></head>
    <body><div class="card">
        <div class="icon">💀</div>
        <h2>Link Expired</h2>
        <p>This link has already been used and is no longer available.<br>Request a new link from the bot.</p>
        <div class="footer">Protected by <span class="brand">Codeflix</span> Security</div>
    </div></body></html>
    """
    return web.Response(text=html, content_type='text/html', status=200)
