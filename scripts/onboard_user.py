import json
import os
import sys
import requests


def get_user_payload():
    """Retrieves user payload from environment variables or a JSON file fallback."""
    first_name = os.environ.get("USER_FIRST_NAME")
    last_name = os.environ.get("USER_LAST_NAME")
    username = os.environ.get("USER_USERNAME")

    if first_name and last_name and username:
        print("--> Loaded user payload from GitHub workflow environment variables.")
        return {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "username": username.strip(),
        }

    payload_path = os.environ.get(
        "PAYLOAD_FILE_PATH", "payloads/new_user_sample.json"
    )
    if os.path.exists(payload_path):
        print(f"--> Loaded user payload from local file: {payload_path}")
        with open(payload_path, "r") as f:
            return json.load(f)

    print("❌ Error: No user parameters found in environment or file.")
    sys.exit(1)


def get_access_token():
    """Retrieves Microsoft Graph API Access Token using OIDC Federated Token from Azure CLI login."""
    # When azure/login@v2 runs, GitHub Action exports AZURE_ACCESSTOKEN or access token via Azure CLI
    # We can fetch a Graph token using the logged-in context via Azure CLI command or OAuth2 endpoint.
    import subprocess

    try:
        cmd = [
            "az",
            "account",
            "get-access-token",
            "--resource-type",
            "ms-graph",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ Error obtaining Graph API access token: {e}")
        sys.exit(1)


def create_entra_user(token, first_name, last_name, username, domain):
    """Creates a new user in Microsoft Entra ID via Microsoft Graph API."""
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    upn = f"{username}@{domain}"
    display_name = f"{first_name} {last_name}"

    payload = {
        "accountEnabled": True,
        "displayName": display_name,
        "givenName": first_name,
        "surname": last_name,
        "mailNickname": username,
        "userPrincipalName": upn,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": "TempPassword123!#",  # Temporary password for first login
        },
    }

    print(f"--> Creating Entra ID user: {upn}...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        user_data = response.json()
        user_id = user_data.get("id")
        print(f"✅ User successfully created in Entra ID! (Object ID: {user_id})")
        return user_id
    elif response.status_code == 409:
        print(f"⚠️ User {upn} already exists in Entra ID.")
        sys.exit(0)
    else:
        print(
            f"❌ Failed to create user ({response.status_code}): {response.text}"
        )
        sys.exit(1)


def add_user_to_group(token, user_id, group_id):
    """Adds the newly created user to an Entra ID Security Group."""
    if not group_id:
        print("ℹ️ No ONBOARDING_GROUP_ID provided. Skipping group assignment.")
        return

    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
    }

    print(f"--> Adding user {user_id} to Entra group {group_id}...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [204, 200]:
        print("✅ User successfully added to the onboarding group!")
    else:
        print(
            f"⚠️ Could not add user to group ({response.status_code}): {response.text}"
        )


def main():
    user_payload = get_user_payload()

    first_name = user_payload.get("first_name")
    last_name = user_payload.get("last_name")
    username = user_payload.get("username")

    azure_domain = os.environ.get("AZURE_DOMAIN")
    group_id = os.environ.get("ONBOARDING_GROUP_ID")

    if not azure_domain:
        print("❌ Error: AZURE_DOMAIN environment variable is missing.")
        sys.exit(1)

    # 1. Get Graph Access Token from Azure CLI session
    token = get_access_token()

    # 2. Provision User
    user_id = create_entra_user(
        token, first_name, last_name, username, azure_domain
    )

    # 3. Assign Group
    if user_id:
        add_user_to_group(token, user_id, group_id)


if __name__ == "__main__":
    main()