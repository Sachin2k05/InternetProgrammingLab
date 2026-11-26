# RoadAid — Lab 25

Local roadside assistance directory with customer and mechanic registration, mechanic license details, admin approval before public listing, service/location search, map links, mechanic business management, and customer feedback.

Run `python server.py` in this folder, then open [http://localhost:8025](http://localhost:8025).

Demo logins:

- Admin: `admin@roadaid.test` / `road123`
- Customer: `driver@roadaid.test` / `driver123`
- Approved mechanic: `ari@roadaid.test` / `mechanic123`

New mechanics remain hidden until an admin approves the submitted license details. Map links open Google Maps using the business coordinates. This prototype does not dispatch mechanics or guarantee emergency response.
