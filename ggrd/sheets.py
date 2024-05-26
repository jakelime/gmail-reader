import os
import warnings
from typing import Optional

import gspread
from gspread.worksheet import Worksheet
import pandas as pd

try:
    from auth import GoogleAuthManager
    from utils import DATETIME_FMT, CustomLogger
except ImportError:
    from ggrd.auth import GoogleAuthManager
    from ggrd.utils import DATETIME_FMT, CustomLogger

APP_NAME = "ggrd"

warnings.filterwarnings("ignore", category=DeprecationWarning)


class GoogleSheetClient:
    def __init__(
        self,
        spreadsheet_id: Optional[str] = None,
        spreadsheet_name: Optional[str] = None,
    ):
        self.lg = CustomLogger(APP_NAME).getLogger()
        self.gga = GoogleAuthManager()
        self.gs = self.gga.get_gspread()
        self.lg.debug("google sheets service loaded")
        if spreadsheet_id is not None:
            self.ss = self.gs.open_by_key(spreadsheet_id)
            self.lg.info(f"spreadsheet loaded - {spreadsheet_id=}")
        elif spreadsheet_name is not None:
            try:
                self.ss = self.gs.open(spreadsheet_name)
                self.lg.info(f"spreadsheet loaded - {spreadsheet_name=}")
            except gspread.exceptions.SpreadsheetNotFound:
                self.lg.error(f"{spreadsheet_name=} not found")
                self.ss = self.gs.create(spreadsheet_name)
                self.lg.info(f"created new spreadsheet - {spreadsheet_name}")
                self.share_spreadsheet(spreadsheet_name)
        else:
            raise ValueError("missing value 'spreadsheet_name' or 'spreadsheet_id'")

    def share_spreadsheet(self, name: str) -> None:
        emails_str = os.getenv("GOOGLE_ACCOUNTS", None)
        if emails_str is None:
            self.lg.warning("missing environment variable GOOGLE_ACCOUNTS")
            return
        emails = [em.strip() for em in emails_str.split(",")]
        for em in emails:
            self.ss.share(em, perm_type="user", role="writer")
            self.lg.info(f"ss({name}) shared with {em}")

    def read_data(self, sheet_name: str = "data") -> pd.DataFrame | None:
        try:
            worksheet = self.ss.worksheet(sheet_name)
        except IndexError:
            self.lg.warning(f"no worksheet named '{sheet_name}'")
            self.ss.add_worksheet(sheet_name, rows=1000, cols=10)
            self.lg.info(f"created {sheet_name=}")
            worksheet = self.ss.worksheet(sheet_name)

        try:
            df = pd.DataFrame(worksheet.get_all_records())
            df["datetime"] = pd.to_datetime(df["datetime"], format=DATETIME_FMT)
            return df
        except Exception as e:
            self.lg.error(f"read data from gsheet({sheet_name=}) failed; {e=}")
            return None

    def update_data(self, dfin: pd.DataFrame, sheet_name: str = "data") -> None:
        df = self.read_data(sheet_name=sheet_name)
        dfin = self.parse_data_for_gsheet(dfin)

        worksheet = self.ss.worksheet(sheet_name)
        current_row = len(df) + 2
        for _, row in dfin.iterrows():
            if (df["booking_ref"].eq(row.booking_ref)).any():
                continue
            range_name = f"A{current_row}"
            worksheet.update(values=[row.tolist()], range_name=range_name)
            current_row += 1
            self.lg.info(f"[worksheet-{sheet_name}]: updated {range_name}")

        self.lg.info(f"updated {current_row-len(df)-2} entries")

    def get_worksheet(self, sheet_name: str) -> Worksheet:
        try:
            worksheet = self.ss.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            self.lg.warning(f"no worksheet named '{sheet_name}'")
            self.ss.add_worksheet(sheet_name, rows=1000, cols=10)
            self.lg.info(f"created {sheet_name=}")
            worksheet = self.ss.worksheet(sheet_name)
        return worksheet

    def reset_and_write_data(self, df: pd.DataFrame, sheet_name: str = "data"):
        worksheet = self.get_worksheet(sheet_name)
        worksheet.clear()
        df = self.parse_data_for_gsheet(df)
        worksheet.update(values=[list(df.columns)], range_name="A1")
        worksheet.update(values=df.values.tolist(), range_name="A2")
        self.lg.info(f"update completed. {df.shape=}")

    def parse_data_for_gsheet(self, dfin: pd.DataFrame) -> pd.DataFrame:
        df = dfin.copy()
        df["datetime"] = df["datetime"].dt.strftime(DATETIME_FMT)
        return df

    def get_last_entry_datetime(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_data()
        if df is None:
            raise RuntimeError("unable to read data")
        ds = df.iloc[-1, :]
        dt = ds["datetime"]
        return dt


def main():
    gsc = GoogleSheetClient(spreadsheet_name=f"{APP_NAME}-Outpost-ClimbRecords")
    ws = gsc.get_worksheet("data")


if __name__ == "__main__":
    main()
