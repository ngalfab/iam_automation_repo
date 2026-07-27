import json
import os
import sys


def get_user_payload():
    """Retrieves user payload from environment variables or a JSON file fallback."""
    # 1. Try reading individual environment variables passed by GitHub Actions
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

    # 2. Fallback: Try reading from a payload JSON file
    payload_path = os.environ.get(
        "PAYLOAD_FILE_PATH", "payloads/new_user_sample.json"
    )
    if os.path.exists(payload_path):
        print(f"--> Loaded user payload from local file: {payload_path}")
        with open(payload_path, "r") as f:
            return json.load(f)

    # 3. If neither source is available, raise an error
    print(
        "❌ Error: No user parameters found in environment variables or payload file."
    )
    sys.exit(1)


def main():
    # 1. Load User Payload
    user_payload = get_user_payload()

    # Extract user attributes
    first_name = user_payload.get("first_name")
    last_name = user_payload.get("last_name")
    username = user_payload.get("username")

    print(
        f"Processing onboarding for: {first_name} {last_name} ({username})..."
    )

    # 2. Load Azure / Entra ID Environment Variables
    azure_domain = os.environ.get("AZURE_DOMAIN")
    group_id = os.environ.get("ONBOARDING_GROUP_ID")

    if not azure_domain:
        print("⚠️ Warning: AZURE_DOMAIN environment variable is not set.")

    # ---------------------------------------------------------
    # TODO: Add your Microsoft Graph API logic below
    # (e.g., Azure identity token acquisition, user creation, group assignment)
    # ---------------------------------------------------------

    print("✅ User payload validated successfully!")


if __name__ == "__main__":
    main()