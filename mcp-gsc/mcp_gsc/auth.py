"""Credential discovery, OAuth token lifecycle, and service construction."""

from __future__ import annotations

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

GSC_CREDENTIALS_PATH = os.environ.get("GSC_CREDENTIALS_PATH")
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSSIBLE_CREDENTIAL_PATHS = [
    GSC_CREDENTIALS_PATH,
    os.path.join(SCRIPT_DIR, "service_account_credentials.json"),
    os.path.join(os.getcwd(), "service_account_credentials.json"),
]
OAUTH_CLIENT_SECRETS_FILE = os.environ.get("GSC_OAUTH_CLIENT_SECRETS_FILE")
if not OAUTH_CLIENT_SECRETS_FILE:
    OAUTH_CLIENT_SECRETS_FILE = os.path.join(SCRIPT_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")
SKIP_OAUTH = os.environ.get("GSC_SKIP_OAUTH", "").lower() in ("true", "1", "yes")
SCOPES = ["https://www.googleapis.com/auth/webmasters"]


def get_gsc_service():
    """Return an authorized Search Console service object."""
    if not SKIP_OAUTH:
        try:
            return get_gsc_service_oauth()
        except Exception as error:
            logger.warning("OAuth authentication failed: %s", error)
    for cred_path in POSSIBLE_CREDENTIAL_PATHS:
        if cred_path and os.path.exists(cred_path):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    cred_path,
                    scopes=SCOPES,
                )
                return build(
                    "searchconsole",
                    "v1",
                    credentials=creds,
                    cache_discovery=False,
                )
            except Exception:
                continue
    fallbacks = ", ".join(path for path in POSSIBLE_CREDENTIAL_PATHS[1:] if path)
    raise FileNotFoundError(
        "Authentication failed. Please either:\n"
        "1. Set up OAuth by placing a client_secrets.json file in the script directory, or\n"
        "2. Set the GSC_CREDENTIALS_PATH environment variable or place a service "
        f"account credentials file in one of these locations: {fallbacks}"
    )


def get_gsc_service_oauth():
    """Return an authorized Search Console service object using OAuth."""
    creds = _load_stored_credentials()
    if not creds or not creds.valid:
        creds = _refresh_credentials(creds)
    if not creds or not creds.valid:
        creds = _run_oauth_flow()
    return build(
        "searchconsole",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )


def _load_stored_credentials():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return None


def _refresh_credentials(creds):
    if not creds or not creds.expired or not creds.refresh_token:
        return creds
    try:
        creds.refresh(Request())
        _write_token(creds)
        return creds
    except Exception:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return None


def _run_oauth_flow():
    if not os.path.exists(OAUTH_CLIENT_SECRETS_FILE):
        raise FileNotFoundError(
            "OAuth client secrets file not found. Please place a client_secrets.json "
            "file in the script directory or set the "
            "GSC_OAUTH_CLIENT_SECRETS_FILE environment variable."
        )
    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token(creds)
    return creds


def _write_token(creds) -> None:
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())


async def reauthenticate() -> str:
    """Delete the current OAuth token and authenticate as a new Google user."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            token_deleted = True
        else:
            token_deleted = False
        if not os.path.exists(OAUTH_CLIENT_SECRETS_FILE):
            return (
                "Error: OAuth client secrets file not found. "
                "Cannot start new authentication flow. "
                "Please ensure client_secrets.json is present or set the "
                "GSC_OAUTH_CLIENT_SECRETS_FILE environment variable."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            OAUTH_CLIENT_SECRETS_FILE,
            SCOPES,
        )
        creds = flow.run_local_server(port=0)
        _write_token(creds)
        message = "Successfully authenticated with a new Google account."
        return "Previous session deleted. " + message if token_deleted else message
    except Exception as error:
        return f"Error during reauthentication: {str(error)}"


__all__ = [
    "GSC_CREDENTIALS_PATH",
    "OAUTH_CLIENT_SECRETS_FILE",
    "POSSIBLE_CREDENTIAL_PATHS",
    "SCOPES",
    "SCRIPT_DIR",
    "SKIP_OAUTH",
    "TOKEN_FILE",
    "get_gsc_service",
    "get_gsc_service_oauth",
    "reauthenticate",
]
