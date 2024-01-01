from pathlib import Path

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ggrd.utils import CustomLogger

APP_NAME = "ggrd"


class GoogleAuthManager:
    def __init__(self):
        self.lg = CustomLogger(name=APP_NAME).getLogger()
        self.emails = []
        self.secrets_dirpath = Path(__file__).parent / "secrets"
        self.creds_file = self.get_credentials_json(self.secrets_dirpath)
        self.token_file = self.secrets_dirpath / "token.json"

        self.SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]  # If modifying these SCOPES, delete the file token.json.
        self.creds = self.get_google_credentials()
        self.lg.debug("google cred initialized")

    def get_google_credentials(self):
        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if self.token_file.is_file():
            creds = Credentials.from_authorized_user_file(self.token_file)

        # If there are no (valid) credentials available, let the user log in.
        if creds is None or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
        return creds

    def get_gmail_service(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=self.creds)
        return service

    def get_credentials_json(self, secrets_dirpath: Path) -> Path:
        json_file = None
        for kw in ["client_secret_*.json", "*credentials.json"]:
            try:
                json_file = next(secrets_dirpath.glob(kw))
            except StopIteration:
                pass
        if json_file is None:
            raise FileNotFoundError("google credentials json file not found")
        return json_file

    def get_sheets_service(self):
        ## Original implementation without gspread library dependencies
        service = build("sheets", "v4", credentials=self.creds)
        return service

    def get_gspread(self):
        return gspread.oauth(
            credentials_filename=self.creds_file,
            authorized_user_filename=self.token_file,
        )
