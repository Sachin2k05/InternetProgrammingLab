# ReNewMarket — Lab 14

A responsive pre-loved marketplace with category/search/condition/price filters, buyer accounts, seller listings, favorites, price offers and counter-offers, order tracking, feedback, and an administrator workspace for users, categories, listings, and transactions.

## Run locally

1. Open a terminal in this folder and run `python server.py` (Python 3 required).
2. Visit [http://localhost:8003](http://localhost:8003).

The server initializes `renewmarket.db` with sample categories, listings, and an administrator account. Demo admin login: `admin@renewmarket.test` / `renew12345`. Join the market to save favorites, make offers, buy listings, or list items. Admin controls are available from the **Admin** link in the footer.

In this classroom demo, checkout creates a transaction record without collecting payment. Logistics are updated as Shipped or Received by the admin, and feedback can be left after an order is marked Received. Real payment processing and delivery integrations are not connected. Product listings and images are sample content; images load from Unsplash.
