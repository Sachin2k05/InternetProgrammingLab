# InsureEasy — Lab 12

A responsive insurance demo with Health, Auto, and Home plans; side-by-side comparison; plan details and applications; role-based admin, agent, and customer dashboards; customer records; policy management; payment and claim records; agent approval; and renewal reminder logs.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8001](http://localhost:8001).

The server initializes `insureeasy.db` automatically using Python's built-in SQLite support. To explore the administrator dashboard, sign in with `admin@insureeasy.test` and password `admin12345`. Use fictional details for any extra accounts.

Agent accounts need administrator approval before they can sign in. Register a new account as an agent, then sign in as the seeded admin and open **Agents** in the dashboard to approve it. Agents can create customer records, add policies, and record SMS reminder messages.

This is a classroom demo. Payments are recorded as simulated entries; there is no card processor or real charge. “SMS” reminders are stored in the database as demo messages; connect an SMS provider to deliver texts. Policy and provider details are sample data, and the password hashes are intended for local demonstration rather than production deployment.
