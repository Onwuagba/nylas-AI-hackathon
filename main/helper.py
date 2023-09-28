import os, requests
from dotenv import load_dotenv
import logging

load_dotenv()
base_url = os.getenv("NYLAS_BASE_URL")
auth = os.getenv("NLYAS_AUTH")
logger = logging.getLogger("server_log")


# confirm email id
def confirm_email_id(email_id):
    """
    Confirms the provided email ID by calling Nylas messages API
    If the email ID is confirmed successfully, the response JSON is printed.

    Args:
        email_id (str): The email ID to confirm.

    Returns:
        None

    Raises:
        ValueError: If the email ID is not provided, or if there is an error confirming the email ID.

    Example:
        ```python
        confirm_email_id("example@example.com")
        ```
    """

    if not email_id:
        raise ValueError("Email id must be provided")

    header = {
        "Accept": "application/json",
        "Authorization": f"Bearer {auth}",
        "Content-Type": "application/json",
    }
    url = f"{base_url}/messages/{email_id}"

    try:
        res = requests.get(url, headers=header, timeout=(60, 90))
        res_json = res.json()
        if res.status_code != 200 or "message" in res_json:
            raise ValueError(res_json.get("message") or "Unable to confirm email id")

        if email_id != res_json.get("id"):
            raise ValueError("Unable to confirm email id")
        print(res_json)
    except Exception as ex:
        logger.error("Error confirming email id: %s", ex)
        raise ValueError(ex.args[0] or "An error occurred confirming email") from ex
