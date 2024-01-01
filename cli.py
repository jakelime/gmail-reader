from ggrd.utils import CustomLogger
from ggrd.outpost import Outpost

APP_NAME = "ggrd"
lg = CustomLogger(APP_NAME).getLogger()


def main():
    op = Outpost()
    # op.reset_data()
    op.pull_updates_from_email()

    # ec.logout()


if __name__ == "__main__":
    main()
