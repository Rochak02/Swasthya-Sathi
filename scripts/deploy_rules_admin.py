"""
deploy_rules_admin.py — Deploy Firestore security rules using the correct REST API format.
The Firebase Rules v1 API uses a specific format for updating releases.
"""
import json
import sys
from pathlib import Path

try:
    import google.oauth2.service_account
    import google.auth.transport.requests
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth", "requests", "-q"])
    import google.oauth2.service_account
    import google.auth.transport.requests
    import requests

SERVICE_ACCOUNT_FILE = Path(__file__).parent / "backend" / "serviceAccountKey.json"
RULES_FILE           = Path(__file__).parent / "firestore.rules"
PROJECT_ID           = "digital-healthcare-ecosystem"

SCOPES = [
    "https://www.googleapis.com/auth/firebase",
    "https://www.googleapis.com/auth/cloud-platform",
]

# Read files
rules_content = RULES_FILE.read_text(encoding="utf-8")
print(f"Loaded rules ({len(rules_content)} chars)")

# Authenticate
creds = google.oauth2.service_account.Credentials.from_service_account_file(
    str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
)
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)
token = creds.token
print("Authenticated")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type":  "application/json",
    "X-Goog-User-Project": PROJECT_ID,
}

BASE = f"https://firebaserules.googleapis.com/v1/projects/{PROJECT_ID}"

# Step 1: Create new ruleset
print("Creating ruleset...")
r = requests.post(f"{BASE}/rulesets", headers=headers, json={
    "source": {"files": [{"name": "firestore.rules", "content": rules_content}]}
})
if r.status_code not in (200, 201):
    print(f"ERROR creating ruleset: {r.status_code} {r.text}")
    sys.exit(1)

ruleset_name = r.json()["name"]
print(f"Ruleset: {ruleset_name}")

# Step 2: List current releases
print("Fetching releases...")
r2 = requests.get(f"{BASE}/releases", headers=headers, params={"filter": "name=cloud.firestore"})
print(f"Releases: {r2.status_code}")

# Try to get the existing release
r3 = requests.get(f"{BASE}/releases/cloud.firestore", headers=headers)
print(f"Get release: {r3.status_code}")

if r3.status_code == 200:
    existing = r3.json()
    print(f"Existing release: {json.dumps(existing, indent=2)}")
    # Use the exact field name from the existing release structure
    existing["rulesetName"] = ruleset_name
    r4 = requests.put(
        f"{BASE}/releases/cloud.firestore",
        headers=headers,
        json=existing
    )
    print(f"PUT result: {r4.status_code}")
    if r4.status_code in (200, 201):
        print("SUCCESS!")
    else:
        print(r4.text[:500])
else:
    print(f"Could not get release: {r3.text[:300]}")
