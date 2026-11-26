# CleanRoute — Lab 22

Local solid-waste management demo with bin records, fill levels, public issue reports, driver accounts and assigned routes, route status, and admin summaries. Admins can generate an area route by nearest-stop ordering of bins that meet a selected fill threshold. Map links use each bin's saved coordinates.

Run `python server.py` in this folder, then open [http://localhost:8022](http://localhost:8022).

Demo logins:

- Admin: `admin@cleanroute.test` / `clean123`
- Driver: `driver@cleanroute.test` / `drive123`
- Public: `neighbor@cleanroute.test` / `public123`

Public users can register reports. Driver registration is available from the join form. This local route planner uses sample coordinates and does not require a Google Maps API key.
