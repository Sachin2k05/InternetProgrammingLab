# BlossomGifts — Lab 13

A responsive flower and gift storefront with occasion/category filters, product search, cart quantity editing, scheduled delivery, gift notes, the `BLOOM15` promotion, order confirmation records, public order tracking, customer accounts and order history, and an admin workspace for inventory, customers, and order status.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8002](http://localhost:8002).

The server creates and initializes `blossomgifts.db` automatically with the sample catalog. Admin demo login: `hello@blossomgifts.test` / `flowers123`. Customer accounts can be created from the account button. Admin inventory lets you add items, change prices, and remove products; the Orders area lets you update delivery status.

The checkout is a demo and does not collect payment. Order confirmations are saved as email/SMS demo records; connect mail and SMS services to send real messages. Product details and prices are sample data. Listing photos load from Unsplash.
