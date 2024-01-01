# Gmail Reader

Uses Google OAuth API to access your own gmail account.

Current example ETL:

- Login to email using OAuth
- Query for email from `no-reply@outpostclimbing.rezeve.com`
- Compiles all the emails into a single `dataframe`
- Data will show details of each time I went to the `outpost gym`


## Quickstart

1. Make sure you have already started a new project on Google Cloud Console `https://console.cloud.google.com/`
1. Enable `Gmail API` and `Google Sheets API`
1. Download credentials file i.e. `client_secret_123241-asdadae.apps.googleusercontent.com`
1. Load the credentials file to `/gmail-reader/grrd/secrets/client_secret_123241-asdadae.apps.googleusercontent.com`
1. Run `python cli.py`