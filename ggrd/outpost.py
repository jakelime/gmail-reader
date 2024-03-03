from ggrd.gmail import OutpostEmailClient
from ggrd.sheets import GoogleSheetClient
from ggrd.utils import CustomLogger

APP_NAME = "ggrd"


class Outpost:
    def __init__(self):
        self.lg = CustomLogger(APP_NAME).getLogger()
        self.email = OutpostEmailClient()
        self.gsc = GoogleSheetClient(spreadsheet_name=f"{APP_NAME}-Outpost-ClimbRecords")

    def pull_updates_from_email(self, self_reset: bool = True) -> None:
        try:
            dt = self.gsc.get_last_entry_datetime()
            df = self.email.run(after_date=dt.strftime("%Y/%m/%d"))
            self.gsc.update_data(df)
        except Exception as e:
            self.lg.error(f"{e=}")
            if self_reset:
                self.lg.warning("attempting self reset...")
                self.reset_data()

    def reset_data(self) -> None:
        df = self.email.run()
        self.gsc.reset_and_write_data(df)
