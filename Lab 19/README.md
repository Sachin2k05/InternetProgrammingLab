# VetCure — Lab 19

A local classroom prototype for farmer and veterinary doctor accounts. Farmers can browse government and private clinics, subscribe, record simulated payment references, submit animal symptoms and image/audio/video attachments, track case status, and read doctor responses. Doctors can review cases, send guidance, manage public care notes and news, and view farmer, payment, and feedback records. Public area summaries aggregate reported disease labels.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8009](http://localhost:8009).

Demo accounts:

- Farmer: `farmer@vetcure.test` / `farm12345`
- Government doctor: `amina@govvet.test` / `govvet123`
- Private doctor: `omar@privatevet.test` / `clinic12345`

New accounts can be registered from the site. Doctors provide their clinic type, consultation fee, and payment details during registration. Government CVH subscriptions are free. Private subscription payments and bank/EasyPaisa references are recorded as classroom simulations; no money is transferred. Uploaded media and records are stored locally in `vetcure.db`.

This is an educational prototype, not a veterinary diagnostic service. Public care notes and doctor replies are not a substitute for in-person veterinary evaluation. Do not use it for urgent or emergency animal care.
