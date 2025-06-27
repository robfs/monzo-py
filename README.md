# monzo-py

A Python library for interacting with your Monzo transactions.

> [!IMPORTANT]
> In order to use this library you must have a paid Monzo account with your transactions exported to a Google Sheet.

## Google Sheets Setup

1. Ensure your Monzo transactions are exported to a Google Sheet and check you can access it.
2. Follow the instructions to enable access to your [Google Sheets via Python](https://developers.google.com/workspace/sheets/api/quickstart/python).

> [!IMPORTANT]
> Make sure you keep a copy of your `credentials.json` file immediately.

3. Within [Data Access](https://console.cloud.google.com/auth/scopes) add the `/auth/spreadsheets.readonly` scope to your project.
4. Within [Audience](https://console.cloud.google.com/auth/audience) add yourself as a test user (this will enable you to access the API without publishing the app).
