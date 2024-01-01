from ggrd.outpost import Outpost
from ggrd.utils import CustomLogger

APP_NAME = "ggrd"
clg = CustomLogger(APP_NAME)
lg = clg.getLogger()


def main():
    op = Outpost()
    # op.reset_data()
    op.pull_updates_from_email()
    # ec.logout()


if __name__ == "__main__":
    main()
    clg.run_cleanup()
