import requests


BASE_URL = "http://127.0.0.1:5000"


# =========================================================
# ADMIN LOGIN
# =========================================================

login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "phone_number": "0928546537",
        "password": "27211616",
    },
)

print("LOGIN STATUS:", login_response.status_code)
print(login_response.json())


if login_response.status_code != 200:
    raise SystemExit("Admin login failed.")


login_data = login_response.json()

token = login_data["data"]["access_token"]


# =========================================================
# CREATE EXTENSION AGENT
# =========================================================

agent_response = requests.post(
    f"{BASE_URL}/api/admin/extension-agents",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    json={
        "phone_number": "0911223344",
        "full_name": "Abebe Extension Agent",
        "password": "Agent12345",
        "region": "Amhara",
        "woreda": "Bahir Dar Zuria",
        "specialization": "Maize Disease",
        "certification_number": "EA-2026-001",
        "preferred_language": "am",
    },
)

print()
print("=" * 60)
print("CREATE EXTENSION AGENT")
print("=" * 60)
print("STATUS:", agent_response.status_code)
print("RESPONSE:")

try:
    print(agent_response.json())
except Exception:
    print(agent_response.text)