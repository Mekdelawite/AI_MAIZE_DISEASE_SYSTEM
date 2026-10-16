import requests


BASE_URL = "http://127.0.0.1:5000"


# =========================================================
# EXTENSION AGENT LOGIN
# =========================================================

login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "phone_number": "0911223344",
        "password": "Agent12345",
    },
)

print("=" * 60)
print("EXTENSION AGENT LOGIN")
print("=" * 60)
print("Status:", login_response.status_code)

if login_response.status_code != 200:
    print(login_response.json())
    raise SystemExit("Extension agent login failed.")

login_data = login_response.json()
token = login_data["data"]["access_token"]

print("Login: SUCCESS")
print("User ID:", login_data["data"]["user"]["id"])
print("Role:", login_data["data"]["user"]["role"])


# =========================================================
# AUTHORIZATION HEADER
# =========================================================

headers = {
    "Authorization": f"Bearer {token}",
}


# =========================================================
# TEST 1 — EXTENSION DIAGNOSES
# =========================================================

print()
print("=" * 60)
print("TEST 1: GET /api/extension/diagnoses")
print("=" * 60)

response = requests.get(
    f"{BASE_URL}/api/extension/diagnoses",
    headers=headers,
)

print("Status:", response.status_code)
print("Response:", response.json())


# =========================================================
# TEST 2 — ADMIN ENDPOINT
# =========================================================

print()
print("=" * 60)
print("TEST 2: EXTENSION AGENT -> ADMIN ENDPOINT")
print("=" * 60)

response = requests.get(
    f"{BASE_URL}/api/admin/extension-agents",
    headers=headers,
)

print("Status:", response.status_code)

try:
    print("Response:", response.json())
except Exception:
    print("Response:", response.text)


# =========================================================
# TEST 3 — CURRENT USER
# =========================================================

print()
print("=" * 60)
print("TEST 3: GET /api/auth/me")
print("=" * 60)

response = requests.get(
    f"{BASE_URL}/api/auth/me",
    headers=headers,
)

print("Status:", response.status_code)
print("Response:", response.json())


print()
print("=" * 60)
print("TESTING COMPLETE")
print("=" * 60)