import warnings
from typing import Optional

import pandas as pd

from ggrd.auth import GoogleAuthManager
from ggrd.utils import DATETIME_FMT, CustomLogger

APP_NAME = "ggrd"

warnings.filterwarnings("ignore", category=DeprecationWarning)


class GoogleSheetClient:
    def __init__(
        self, spreadsheet_id: str = "162NnzVFuBGUb0JBTY0G2h2Jmb6SsrV3xLAUovS_ob_Q"
    ):
        self.lg = CustomLogger(APP_NAME).getLogger()
        self.spreadsheet_id = spreadsheet_id
        self.gga = GoogleAuthManager()
        self.gs = self.gga.get_gspread()
        self.lg.debug("google sheets service loaded")
        self.ss = self.gs.open_by_key(self.spreadsheet_id)

    def read_data(self, sheet_name: str = "data") -> pd.DataFrame:
        try:
            worksheet = self.ss.worksheet(sheet_name)
            df = pd.DataFrame(worksheet.get_all_records())
            df["datetime"] = pd.to_datetime(df["datetime"], format=DATETIME_FMT)
            return df
        except Exception as e:
            self.lg.error(f"read data from gsheet({sheet_name=}) failed; {e=}")
            return pd.DataFrame()

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

    def reset_and_write_data(self, df: pd.DataFrame, sheet_name: str = "data"):
        worksheet = self.ss.worksheet(sheet_name)
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
        ds = df.iloc[-1, :]
        dt = ds["datetime"]
        return dt
