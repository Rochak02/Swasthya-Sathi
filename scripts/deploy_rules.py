"""
deploy_rules.py  —  Deploy Firestore security rules via Firebase REST API
Uses the service account key to authenticate and push rules.
Run: python deploy_rules.py
"""

import json
import time
import sys
from pathlib import Path

try:
    import google.auth
    import google.oauth2.service_account
    import google.auth.transport.requests
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth", "requests", "-q"])
    import google.oauth2.service_account
    import google.auth.transport.requests
    import requests

# ── Config ────────────────────────────────────────────────────────────────────
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "backend" / "serviceAccountKey.json"
RULES_FILE           = Path(__file__).parent / "firestore.rules"
PROJECT_ID           = "digital-healthcare-ecosystem"

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/firebase",
]

# ── Read files ────────────────────────────────────────────────────────────────
if not SERVICE_ACCOUNT_FILE.exists():
    print(f"ERROR: Service account key not found at {SERVICE_ACCOUNT_FILE}")
    sys.exit(1)

rules_content = RULES_FILE.read_text(encoding="utf-8")
print(f"Loaded rules ({len(rules_content)} chars)")

# ── Authenticate ──────────────────────────────────────────────────────────────
creds = google.oauth2.service_account.Credentials.from_service_account_file(
    str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
)
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)
token = creds.token
print("Authenticated with service account")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type":  "application/json",
}

# ── Step 1: Create a new ruleset ──────────────────────────────────────────────
ruleset_url = f"https://firebaserules.googleapis.com/v1/projects/{PROJECT_ID}/rulesets"

ruleset_body = {
    "source": {
        "files": [{
            "name":    "firestore.rules",
            "content": rules_content,
        }]
    }
}

print("Creating new ruleset...")
r = requests.post(ruleset_url, headers=headers, json=ruleset_body)
if r.status_code not in (200, 201):
    print(f"ERROR creating ruleset: {r.status_code}")
    print(r.text)
    sys.exit(1)

ruleset_name = r.json()["name"]
print(f"Ruleset created: {ruleset_name}")

# ── Step 2: Update the release to point to the new ruleset ───────────────────
release_name    = f"projects/{PROJECT_ID}/releases/cloud.firestore"
release_url     = f"https://firebaserules.googleapis.com/v1/projects/{PROJECT_ID}/releases"
release_get_url = f"https://firebaserules.googleapis.com/v1/{release_name}"

r2 = requests.get(release_get_url, headers=headers)

if r2.status_code == 200:
    # Existing release: update using Firebase Rules API format
    print("Updating existing Firestore release...")
    patch_url = f"https://firebaserules.googleapis.com/v1/{release_name}"
    # Firebase Rules v1 uses snake_case in REST bodies
    r3 = requests.patch(
        patch_url,
        headers=headers,
        json={"name": release_name, "ruleset_name": ruleset_name},
        params={"updateMask": "ruleset_name"}
    )
    if r3.status_code in (200, 201):
        print(f"SUCCESS: Firestore rules deployed!")
        print(f"  Release: {release_name}")
        print(f"  Ruleset: {ruleset_name}")
    else:
        print(f"PATCH failed: {r3.status_code} — {r3.text[:400]}")
        print("Ruleset was created but release update failed. Manually link the ruleset in Firebase Console.")
        print(f"  Ruleset: {ruleset_name}")
else:
    # No existing release — create one
    print("Creating new Firestore release...")
    r3 = requests.post(
        release_url,
        headers=headers,
        json={"name": release_name, "rulesetName": ruleset_name}
    )
    if r3.status_code in (200, 201):
        print(f"SUCCESS: Firestore rules deployed!")
    else:
        print(f"ERROR creating release: {r3.status_code}")
        print(r3.text)

print("\nDone. Firestore security rules are now live.")

