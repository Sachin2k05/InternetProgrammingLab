# ComplainEase — Lab 16

A responsive complaint-resolution demo with citizen and officer accounts, complaint submission, map pins and Google Maps links, document/photo evidence, status history, officer notes and proof of work, citizen feedback, FAQ search, and an administrator workspace for accounts, officer logins, assignments, categories, feature visibility, and contact details.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8005](http://localhost:8005).

The server creates `complainease.db` with sample categories and a ComplainEase administrator account. Demo admin login: `admin@complainease.test` / `resolve12345`.

Citizens can register directly. Officer self-registration needs admin approval; an admin can also create an approved officer login in **Officers**. Submitted complaints can be assigned from **All complaints**. Complaint history and uploaded evidence remain in the admin record if an account is removed.

Email and SMS updates are recorded as in-app demo notifications. Connect a messaging provider to deliver real messages. The map uses OpenStreetMap tiles and includes a link to the pinned location in Google Maps; the place search uses OpenStreetMap’s public geocoder.
