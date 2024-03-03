import base64
import dataclasses
import os
import tempfile
from typing import Optional

import pandas as pd

try:
    from auth import GoogleAuthManager
    from utils import CustomLogger
except ImportError:
    from ggrd.auth import GoogleAuthManager
    from ggrd.utils import CustomLogger

APP_NAME = "ggrd"


@dataclasses.dataclass
class EmailContent:
    sender: str
    subject: str
    body_text: str
    df: Optional[pd.DataFrame] = None

    def __post_init__(self, preview_length: int = 50):
        self.body_preview = (
            self.body_text
            if len(self.body_text) < preview_length
            else self.body_text[:preview_length]
        )


class EmailClient:
    def __init__(self):
        self.lg = CustomLogger(name=APP_NAME).getLogger()
        self.emails = []
        self.gga = GoogleAuthManager()
        self.service = self.gga.get_gmail_service()
        self.lg.info("gmail service loaded")

    def get_messages(
        self,
        user_id="me",
        sender_email: Optional[str] = None,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 0,
    ):
        try:
            # Build a query string to filter messages by sender
            query_parts = []
            if sender_email:
                query_parts.append(f"from:{sender_email}")
            if before_date:
                query_parts.append(f"before:{before_date}")
            if after_date:
                query_parts.append(f"after:{after_date}")
            if subject:
                query_parts.append(f"subject:{subject}")

            query = " ".join(query_parts)

            # Get a list of messages thatÏ match the query
            response = (
                self.service.users().messages().list(userId=user_id, q=query).execute()
            )
            messages = response.get("messages", [])

            # Print the subject and sender of each message
            for i, message in enumerate(messages, 1):
                e = self.get_message(message_id=message["id"], user_id=user_id)
                self.emails.append(e)
                if limit:
                    if i >= limit:
                        break

        except Exception as error:
            self.lg.info(f"An error occurred: {error}")

    def get_message(self, message_id, user_id="me") -> EmailContent:
        msg = (
            self.service.users().messages().get(userId=user_id, id=message_id).execute()
        )
        headers = msg["payload"]["headers"]
        subject = next(
            (header["value"] for header in headers if header["name"] == "Subject"),
            "No Subject",
        )
        sender = next(
            (header["value"] for header in headers if header["name"] == "From"),
            "No Sender",
        )

        # Get the content of the email
        payload = msg["payload"]
        decoded_body = None
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body = part["body"]["data"]
                    decoded_body = base64.urlsafe_b64decode(body).decode("utf-8")
                    raise NotImplementedError("Not implemented - email in text")
                    break  # Stop after finding the first text/plain part
        else:
            # If the email has no parts, assume it is plaintext
            body = payload["body"]["data"]
            decoded_body = base64.urlsafe_b64decode(body).decode("utf-8")

        body = decoded_body if decoded_body is not None else "No Body"

        return EmailContent(sender=sender, subject=subject, body_text=body)

    def run(self, before_date: Optional[str] = None, after_date: Optional[str] = None):
        # Get and print the messages in the user's inbox
        self.get_messages(before_date=before_date, after_date=after_date)

    def logout(self):
        os.remove(self.service.token)
        self.lg.info("logout successful")


class OutpostEmailClient(EmailClient):
    def __init__(self):
        super().__init__()
        self.kws = {
            "Date & time": "datetime",
            "Booking ref": "booking_ref",
            "Membership No": "membership_no",
            "Membership": "membership_name",
            "Class": "class_name",
            "Location": "location",
        }

    def run(self, after_date: Optional[str] = None) -> pd.DataFrame:
        # Get and print the messages in the user's inbox
        self.get_messages(
            sender_email="no-reply@outpostclimbing.rezeve.com",
            after_date=after_date,
            subject="Booking confirmed:",
            limit=0,
        )
        df = self.consolidate_all_emails()
        return df

    def print_emails(self) -> None:
        for email in self.emails:
            print(email.df)

    def parse_html(self, html_str: str) -> pd.DataFrame:
        dfs = [None]
        with tempfile.NamedTemporaryFile(delete=True) as fp:
            with open(fp.name, "w") as fwriter:
                fwriter.write(html_str)
            dfs = pd.read_html(fp)  # type: ignore
        for df in dfs:
            dff = df[df[0].isin(self.kws)]
            if len(dff) < len(self.kws):
                continue
            else:
                df = dff.copy()
                df[0] = df[0].replace(self.kws)
                df.set_index(0, inplace=True)
                df = df.T
                df["datetime"] = pd.to_datetime(
                    df["datetime"], format="%d %b %Y @ %H:%M %p", errors="raise"
                )
                return df
        return pd.DataFrame()

    def get_message(self, message_id, user_id="me") -> EmailContent:
        e = super().get_message(message_id, user_id)
        df = self.parse_html(e.body_text)
        return EmailContent(
            sender=e.sender, subject=e.subject, body_text=e.body_text, df=df
        )

    def consolidate_all_emails(self) -> pd.DataFrame:
        df = pd.concat([email.df for email in self.emails])
        df.sort_values(by="datetime", inplace=True, ascending=True)
        df.reset_index(drop=True, inplace=True)
        df = df[self.kws.values()]
        return df


def main():
    ec = EmailClient()

if __name__ == "__main__":
    main()