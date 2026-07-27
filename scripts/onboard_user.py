import os
import json
import secrets
import string
import requests
from azure.identity import DefaultAzureCredential

# ---------------------------------------------------------------------------
# Configuration (Environment Variables populated by GitHub Secrets)
# ---------------------------------------------------------------------------
ORGANIZATION_DOMAIN = os.getenv("AZURE_DOMAIN", "yourdomain.com")
GROUP_ID = os.getenv("ONBOARDING_GROUP_ID")
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd)
                and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*" for c in pwd)):
            return pwd


def get_token():
    """Fetches Microsoft Graph access token using DefaultAzureCredential (OIDC compatible)."""
    credential = DefaultAzureCredential()
    token_object = credential.get_token("https://graph.microsoft.com/.default")
    return token_object.token


def onboard_user(user_data):
    token = get_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    temp_password = generate_secure_password()
    upn = f"{user_data['username']}@{ORGANIZATION_DOMAIN}"

    payload = {
        "accountEnabled": True,
        "displayName": f"{user_data['first_name']} {user_data['last_name']}",
        "givenName": user_data['first_name'],
        "surname": user_data['last_name'],
        "mailNickname": user_data['username'],
        "userPrincipalName": upn,
        "department": user_data.get('department'),
        "jobTitle": user_data.get('job_title'),
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": temp_password
        }
    }

    # 1. Create User
    res = requests.post(f"{GRAPH_BASE_URL}/users", headers=headers, json=payload)
    if res.status_code != 201:
        print(f"::error::Failed to create user: {res.text}")
        exit(1)

    user_obj = res.json()
    print(f"Successfully created user: {user_obj['displayName']} ({user_obj['id']})")

    # 2. Assign to Group (RBAC)
    if GROUP_ID:
        group_payload = {"@odata.id": f"{GRAPH_BASE_URL}/directoryObjects/{user_obj['id']}"}
        group_res = requests.post(
            f"{GRAPH_BASE_URL}/groups/{GROUP_ID}/members/$ref",
            headers=headers,
            json=group_payload
        )
        if group_res.status_code == 204:
            print(f"Successfully added user to group {GROUP_ID}")


if __name__ == "__main__":
    # Reads payload passed from GitHub Action runner
    raw_payload = os.getenv("USER_PAYLOAD")
    if not raw_payload:
        print("::error::No user payload found in environment.")
        exit(1)
        
    # ✅ Construct payload directly from environment variables
user_payload = {
    "first_name": os.environ.get("USER_FIRST_NAME"),
    "last_name": os.environ.get("USER_LAST_NAME"),
    "username": os.environ.get("USER_USERNAME")
}