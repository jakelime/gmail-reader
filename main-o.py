from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


class EmailClient:
    def __init__(self):
        self.SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly"
        ]  # If modifying these SCOPES, delete the file token.json.
        self.cwd = Path(__file__).parent
        self.creds = None
        token_file = self.cwd / "token.json"
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if token_file.is_file():
            self.creds = Credentials.from_authorized_user_file(token_file)

        # If there are no (valid) credentials available, let the user log in.
        if self.creds is None or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.get_credentials_json(), self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())

        # Build the Gmail API service
        self.service = build("gmail", "v1", credentials=self.creds)

    def get_credentials_json(self) -> Path:
        json_file = None
        for kw in ["client_secret_*.json", "*credentials.json"]:
            try:
                json_file = next(self.cwd.glob(kw))
            except StopIteration:
                pass
        if json_file is None:
            raise FileNotFoundError("google credentials json file not found")
        return json_file

    def get_gmail_service(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        # Build the Gmail API service
        service = build("gmail", "v1", credentials=creds)
        return service

    def get_messages(self, service, user_id="me", label_ids=["INBOX"]):
        try:
            # Get a list of messages
            response = (
                service.users()
                .messages()
                .list(userId=user_id, labelIds=label_ids)
                .execute()
            )
            messages = response.get("messages", [])

            # Print the subject and sender of each message
            for i, message in enumerate(messages):
                msg = (
                    service.users()
                    .messages()
                    .get(userId=user_id, id=message["id"])
                    .execute()
                )
                headers = msg["payload"]["headers"]
                subject = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"] == "Subject"
                    ),
                    "No Subject",
                )
                sender = next(
                    (header["value"] for header in headers if header["name"] == "From"),
                    "No Sender",
                )
                print(f"Email #{i}\n   From: {sender}, '{subject}'")
                if i >= 10:
                    break

        except Exception as error:
            print(f"An error occurred: {error}")

    def run(self):
        # Get and print the messages in the user's inbox
        self.get_messages(self.service)


def main():
    ec = EmailClient()
    ec.run()


if __name__ == "__main__":
    main()
