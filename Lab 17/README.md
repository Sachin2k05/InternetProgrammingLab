# VoteOnline — Lab 17

A classroom e-voting prototype with voter-ID verification, separate login and voting OTP steps, candidate information, ward eligibility, voter list creation/import, election setup, one-vote enforcement, anonymous ballot rows, voting history, and aggregate results.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8006](http://localhost:8006).

Demo admin login: `admin@voteonline.test` / `ballot12345`. Create wards, create an election, add candidates, add or import voter records, allocate voters to elections, then set the election status to **Open**. Close it to show public aggregate results.

OTP codes are displayed in the browser as demo codes; no real email or SMS is sent. This project is for classroom demonstration only. It has not undergone an election security audit and must not be used to conduct a real election or make legally binding decisions.
