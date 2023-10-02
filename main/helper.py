import ast
import os, requests
import openai
from dotenv import load_dotenv
import logging

load_dotenv()
base_url = os.getenv("NYLAS_BASE_URL")
auth = os.getenv("NLYAS_AUTH")
logger = logging.getLogger("server_log")

openai.api_key = os.getenv("OPEN_AI_TOKEN")


# confirm email id
def confirm_email_and_participants(email_id):
    """
    Confirms the provided email ID by calling Nylas messages API
    If the email ID is confirmed successfully, the response JSON is printed.

    Args:
        email_id (str): The email ID to confirm.

    Returns:
        None

    Raises:
        ValueError: If the email ID is not provided, or if there is an error confirming the email ID.

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
        return _confirm_email_extract(url, header, email_id)
    except Exception as ex:
        logger.error("Error confirming email id: %s", ex)
        raise ValueError(ex.args[0] or "An error occurred confirming email") from ex


def _confirm_email_extract(url, header, email_id):
    """
    The method retrieves the email participants from the JSON object and returns them as a list.

    Args:
        json_obj: The JSON object containing the email details.

    Returns:
        List[str]: A list of email participants.

    Raises:
        ValueError: Raised when the email confirmation fails or the email participants cannot be retrieved.

    """
    res = requests.get(url, headers=header, timeout=(60, 90))
    res_json = res.json()
    if res.status_code != 200 or "message" in res_json:
        raise ValueError(res_json.get("message") or "Unable to confirm email id")

    if email_id != res_json.get("id"):
        raise ValueError("Unable to confirm email id")

    if email_participants := confirm_email_participant(res_json):
        return email_participants
    else:
        raise ValueError("Email participants cannot be retrieved at this time")


def confirm_email_participant(json_obj):
    email_list = []

    if obj_list := json_obj.get("cc"):
        for emails in obj_list:
            email_list.extend(em.get("email") for em in emails)
    email_list.extend(
        (
            json_obj.get("from")[0].get("email"),
            json_obj.get("to")[0].get("email"),
        )
    )
    return email_list


def auto_create_annotation(text):
    if not text:
        raise ValueError("Please provide a text to create an annotation")

    if len(text) > 300:
        raise ValueError("Text cannot exceed 300 characters")

    prompt = f"Given the user input '{text}', categorize the text under one or more of the following labels:\n- Task\n- Meeting Request\n- Follow-up\n- Question\n- Deadline\n- Approval\n- Feedback\n- Review. Ensure the response returns a python dictionary with the format 'Category: <label>, Annotation: <selected_text>', with no additional text."

    try:
        response = openai.Completion.create(
            engine="text-davinci-003", prompt=prompt, max_tokens=200
        )

        res = response.choices[0].text.strip().replace("\n", "").split(";")
        print(res)
        resp = []

        for val in res:
            if "Category" not in val:
                new_val = val.split(":")
                resp.append({"Category": new_val[0], "Annotation": new_val[1]})
            elif isinstance(val, str):
                response_dict = ast.literal_eval(val)
                if isinstance(response_dict, dict):
                    resp.append(response_dict)
                else:
                    for vv in response_dict:
                        resp.append(vv)

            else:
                resp = res

        return resp

    except Exception as ex:
        logger.error("Error generating annotation for text:%s,  %s", text, ex)
        return "Error generating annotation"
