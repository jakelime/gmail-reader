import base64
from collections import OrderedDict
import dataclasses
import io
import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import gspread
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

APP_NAME = "ggrd"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class GoogleAuthManager:
    def __init__(self):
        self.lg = CustomLogger(name=APP_NAME).getLogger()
        self.emails = []
        # self.token = self.get_gmail_service()
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

    def get_sheets_service0(self):
        ## Original implementation without gspread library dependencies
        service = build("sheets", "v4", credentials=self.creds)
        return service

    def get_sheets_service(self):
        return gspread.oauth(
            credentials_filename=self.creds_file,
            authorized_user_filename=self.token_file,
        )


class CustomLogger:
    def __init__(
        self,
        name: str = __name__,
        level: str = "INFO",
        logfile_dirpath: Path | str | None = None,
        console_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        console_datefmt: str = DATETIME_FMT,
        logfile_fmt: str = "[%(asctime)s]%(levelname)-5s: %(message)s",
        logfile_datefmt: str = DATETIME_FMT,
        rotating_maxBytes: int = 2_097_152,
        rotating_backupCount: int = 5,
    ):
        self.name = name
        self.level = level
        self.console_fmt = logging.Formatter(fmt=console_fmt, datefmt=console_datefmt)
        self.logfile_fmt = logging.Formatter(fmt=logfile_fmt, datefmt=logfile_datefmt)
        self.rotating_maxBytes = rotating_maxBytes
        self.rotating_backupCount = rotating_backupCount
        match logfile_dirpath:
            case Path():
                pass
            case str():
                logfile_dirpath = Path(logfile_dirpath)
            case _:
                logfile_dirpath = Path(__file__).parent

        self.logfilepath = logfile_dirpath / f"{self.name}.log"
        self.logger = None
        self.getLogger()

    def make_logger(self, logger) -> logging.Logger:
        try:
            logger.setLevel(self.level)
            c_handler = logging.StreamHandler()
            c_handler.setFormatter(self.console_fmt)
            c_handler.setLevel(self.level)
            logger.addHandler(c_handler)
            f_handler = RotatingFileHandler(
                self.logfilepath,
                maxBytes=self.rotating_maxBytes,
                backupCount=self.rotating_backupCount,
            )
            f_handler.setFormatter(self.logfile_fmt)
            f_handler.setLevel(self.level)
            logger.addHandler(f_handler)
            logger.debug(f"logger initialized - {self.logfilepath}")
            return logger
        except Exception as e:
            print(f"logger init failed, {e=}")
            raise e

    def getLogger(self):
        logger = logging.getLogger(self.name)
        if logger.hasHandlers():
            return logger
        return self.make_logger(logger)


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
        self.lg.info("gmail service built")

    def get_messages(
        self,
        user_id="me",
        sender_email: Optional[str] = None,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None,
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
        os.remove(self.token)
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


class GoogleSheetClient:
    def __init__(
        self, spreadsheet_id: str = "162NnzVFuBGUb0JBTY0G2h2Jmb6SsrV3xLAUovS_ob_Q"
    ):
        self.lg = CustomLogger(APP_NAME).getLogger()
        self.spreadsheet_id = spreadsheet_id
        self.gga = GoogleAuthManager()
        self.service = self.gga.get_sheets_service()
        self.lg.debug("google sheets service built")
        self.ss = self.service.open_by_key(self.spreadsheet_id)

    def read_data(self, sheet_name: str = "data") -> pd.DataFrame:
        try:
            worksheet = self.ss.worksheet(sheet_name)
            df = pd.DataFrame(worksheet.get_all_records())
            df["datetime"] = pd.to_datetime(df["datetime"], format=DATETIME_FMT)
            return df
        except Exception as e:
            self.lg.error(f"read data from gsheet({sheet_name=}) failed; {e=}")
            return pd.DataFrame()

    def write_data(self, df: pd.DataFrame, sheet_name: str = "data"):
        worksheet = self.ss.worksheet(sheet_name)
        range_name = "A2"
        worksheet.update(values=[["hello", "world"], ["a", "b"]], range_name="C1")

    def reset_and_write_data(self, df: pd.DataFrame, sheet_name: str = "data"):
        worksheet = self.ss.worksheet(sheet_name)
        worksheet.clear()
        df = self.parse_data_for_gsheet(df)
        worksheet.update(values=[list(df.columns)], range_name="A1")
        worksheet.update(values=df.values.tolist(), range_name="A2")

    def parse_data_for_gsheet(self, dfin: pd.DataFrame) -> pd.DataFrame:
        df = dfin.copy()
        df["datetime"] = df["datetime"].dt.strftime(DATETIME_FMT)
        return df

    def read_data0(self, range_name: str = "raw!A1:C9999"):
        ## Original implementation without gspread library dependencies
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_name)
                .execute()
            )
            values = result.get("values", [])

            if not values:
                print("No data found.")
            else:
                print("Name, Major:")
                for row in values:
                    # Print columns A and B
                    print(f"{row[0]}, {row[1]}")

        except Exception as error:
            print(f"An error occurred: {error}")

    def get_last_entry_datetime(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_data()
        ds = df.iloc[-1, :]
        dt = ds["datetime"]
        return dt


class Outpost:
    def __init__(self):
        self.email = OutpostEmailClient()
        # df_emails = self.email.run()
        # print(df_emails)
        gs = GoogleSheetClient()
        # gs.reset_and_write_data(df_emails)
        # df = gs.read_data()
        # print(df.info())
        # print(df)
        dt = gs.get_last_entry_datetime()
        df = self.email.run(after_date=dt.strftime("%Y/%m/%d"))
        print(df)


def main():
    op = Outpost()

    # ec.logout()


if __name__ == "__main__":
    main()
