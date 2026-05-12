# QuickStock ERP Core 📦

Welcome to **QuickStock**! This is a lightweight, purely Python-based ERP engine designed to handle the most critical part of any business: **Inventory and Billing**. 

## Why We Built This
Many small businesses rely on manual Excel sheets to manage their inventory. The problem? Excel doesn't stop you from accidentally selling 10 laptops when you only have 5 in the back room. On the other hand, full-blown ERP systems (like SAP or Frappe) are often too heavy, expensive, and complex for a simple local shop.

We built QuickStock to sit right in the middle: a fast, zero-configuration Python script backed by a local SQLite database that **strictly enforces inventory rules**. It guarantees data integrity—meaning you can *never* oversell an item, and you'll never have corrupted, half-saved invoices.

## Key Features 
* **Dynamic Stock Calculation**: Instead of constantly adding and subtracting from a `current_stock` column (which can cause database race conditions), QuickStock calculates stock on the fly. It takes your opening stock and subtracts your total historical sales. The stock number is a 100% accurate reflection of your ledger.
* **Strict Transaction Management**: Creating an invoice involves writing to multiple tables. If a customer tries to buy 5 different items, and the 4th item fails due to low stock, QuickStock catches the error and triggers a complete database rollback (`conn.rollback()`). This ensures no partial data is ever saved.
* **Beautiful Receipts**: Because an ERP isn't complete without a receipt, the system dynamically queries the DB after a successful transaction to generate a clean, formatted receipt right in the terminal.

## The Tech Stack 
* **Python**: The core logic engine.
* **SQLite (`sqlite3`)**: Built directly into Python, requiring zero server setup. Perfect for a portable ERP prototype.
* **UUID**: Used to generate secure, non-sequential Invoice IDs (`INV-2A2A5B80`) to protect business intelligence.

## How to Run It 
Since everything is built-in, you don't need to install any external libraries! Just run the script:

```bash
python quickstock.py
```

### 💡 A Note on Testing
QuickStock uses a persistent database file (`quickstock.db`). Every time you run the script, your stock will continue to drain based on your test orders. 
* If your script suddenly throws a `ValueError` saying you don't have enough stock, **it means your logic is working perfectly!** You simply ran out of test items.
* **To reset everything back to 100 stock:** Just delete the `quickstock.db` file from the folder and run the script again. It will automatically rebuild the database and restock your items.

## Future Scope 
Right now, QuickStock is a monolithic backend engine. Because the database operations are cleanly separated into functions, the logical next steps are:
1. Wrapping the functions in a **FastAPI** layer to create a REST API.
2. Building a frontend dashboard (like **React** or **Vue**) to interact with it.
3. Adding a `tabPurchaseInvoice` table so we can dynamically *add* to our stock, rather than just selling from our initial opening stock.
