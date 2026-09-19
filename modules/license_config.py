"""
Central config for licensing + auto-update.  EDIT THE THREE VALUES BELOW.

Everything the client needs to talk to your server lives here so you never have
to touch 1.2.py again to change the URL or rotate the update key.  Each value can
also be overridden at runtime with an environment variable (handy for testing
against a local server without editing this file).
"""
import os

# 1) Your deployed license/update server.  For local testing use
#    http://127.0.0.1:8000 .  In production this MUST be https:// (tokens ride
#    on it).  Override at runtime with:  set EDUCAM_SERVER=...
SERVER = os.environ.get("EDUCAM_SERVER", "http://127.0.0.1:8000").rstrip("/")

# 2) The version THIS build of the client is.  Bump it every time you ship a new
#    build so the updater can tell when the server has something newer.
APP_VERSION = os.environ.get("EDUCAM_APP_VERSION", "1.29.0")

# 3) The Ed25519 PUBLIC update key.  Generate the pair once on the server with
#       python sign_release.py --genkeys
#    then paste the printed base64 value here.  Until you do, auto-update is
#    disabled (the client refuses to trust an unsigned/unknown update).
#    (Pre-filled with the key whose PRIVATE half is server/update_private.pem.
#     If you regenerate keys with sign_release.py --genkeys, paste the new one.)
UPDATE_PUBLIC_KEY = os.environ.get(
    "EDUCAM_UPDATE_PUBKEY",
    "/4d/5IAkBo2Jq83204KzF3SHjnBlmGZg+V0EYfqyYx4=",
)

# Network timeouts (seconds). HTTP_TIMEOUT is generous because a free host
# (e.g. Render's free tier) puts the server to sleep when idle and the first
# request has to wait ~30-50s for it to wake back up.
HTTP_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 300


def update_key_ready() -> bool:
    """True once you've pasted a real public key (auto-update is armed)."""
    return bool(UPDATE_PUBLIC_KEY) and "PASTE_" not in UPDATE_PUBLIC_KEY
