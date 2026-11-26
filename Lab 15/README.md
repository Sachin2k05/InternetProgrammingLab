# EasyToll — Lab 15

A responsive toll-payment demo with driver registration, vehicle management, an eWallet, prepaid tickets, pass applications and renewals, QR generation, gate scanning/ID verification, toll location updates, trip history, and administrator approvals.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8004](http://localhost:8004).

The server creates `easytoll.db` and adds sample toll locations on first launch. Demo admin login: `admin@easytoll.test` / `toll12345`.

For a toll-gate operator, register a Toll-gate operator account. The admin approves the login in **Users**. The operator then signs in and registers their location in **Gate location**. The admin approves that location in **Approvals** before QR scanning is enabled.

Wallet credits and toll payments are demo records; the project does not connect to a bank or charge real money. Frequent-route entries are saved as preferences; no scheduled debits run. QR rendering and camera scanning use browser libraries loaded from public CDNs; you can also verify by entering the QR code text.
