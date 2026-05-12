import sqlite3
import uuid
from datetime import date

DB_FILE = 'quickstock.db'

def get_db():
    # quick helper for the connection
    return sqlite3.connect(DB_FILE)

def init_db():
    # set up all the tables we need. 
    # using 'tab' prefix like erpnext does.
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS tabItem (
        item_code TEXT PRIMARY KEY,
        item_name TEXT,
        valuation_rate REAL,
        opening_stock INTEGER
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS tabCustomer (
        customer_id TEXT PRIMARY KEY,
        customer_name TEXT,
        email TEXT
    )
    ''')
    
    # header table for invoices
    c.execute('''
    CREATE TABLE IF NOT EXISTS tabSalesInvoice (
        invoice_id TEXT PRIMARY KEY,
        customer_id TEXT,
        posting_date TEXT,
        grand_total REAL,
        FOREIGN KEY (customer_id) REFERENCES tabCustomer (customer_id)
    )
    ''')
    
    # line items linked to the invoice header
    c.execute('''
    CREATE TABLE IF NOT EXISTS tabInvoiceItem (
        parent_id TEXT,
        item_code TEXT,
        qty INTEGER,
        rate REAL,
        amount REAL,
        FOREIGN KEY (parent_id) REFERENCES tabSalesInvoice (invoice_id),
        FOREIGN KEY (item_code) REFERENCES tabItem (item_code)
    )
    ''')
    
    conn.commit()
    conn.close()

def create_invoice(customer_id, items_list):
    # handles the creation of the invoice and line items in one go
    conn = get_db()
    c = conn.cursor()
    
    try:
        grand_total = 0
        lines_to_insert = []
        
        # calculate totals and validate stock first before doing any DB inserts
        for item in items_list:
            icode = item['item_code']
            qty = item['qty']
            rate = item['rate']
            
            # fail early if we don't have enough stock
            current_stock = check_stock(icode)
            if qty > current_stock:
                raise ValueError(f"Not enough stock for {icode}. Tried to sell {qty}, but only have {current_stock}")
                
            row_total = qty * rate
            grand_total += row_total
            lines_to_insert.append({
                'item_code': icode,
                'qty': qty,
                'rate': rate,
                'amount': row_total
            })
            
        # generate a random invoice ID
        inv_id = "INV-" + str(uuid.uuid4())[:8].upper()
        today_date = date.today().isoformat()
        
        # write the header
        c.execute('''
        INSERT INTO tabSalesInvoice (invoice_id, customer_id, posting_date, grand_total)
        VALUES (?, ?, ?, ?)
        ''', (inv_id, customer_id, today_date, grand_total))
        
        # write the children
        for line in lines_to_insert:
            c.execute('''
            INSERT INTO tabInvoiceItem (parent_id, item_code, qty, rate, amount)
            VALUES (?, ?, ?, ?, ?)
            ''', (inv_id, line['item_code'], line['qty'], line['rate'], line['amount']))
            
        conn.commit()
        return inv_id
        
    except Exception as e:
        # if anything failed above (like stock validation), rollback the whole transaction
        conn.rollback()
        print(f"Failed to save invoice: {e}")
        raise
    finally:
        conn.close()

def check_stock(item_code):
    # calculates actual stock by subtracting total sold from the opening stock
    conn = get_db()
    c = conn.cursor()
    
    # what did we start with?
    c.execute('SELECT opening_stock FROM tabItem WHERE item_code = ?', (item_code,))
    res = c.fetchone()
    
    if not res:
        conn.close()
        raise ValueError(f"Item {item_code} doesn't exist.")
        
    opening = res[0]
    
    # how many have we sold so far?
    c.execute('SELECT SUM(qty) FROM tabInvoiceItem WHERE item_code = ?', (item_code,))
    sales = c.fetchone()
    
    sold_qty = sales[0] if sales[0] else 0
    actual_stock = opening - sold_qty
    
    conn.close()
    return actual_stock

def print_receipt(invoice_id):
    # fetches the invoice from the DB and prints a nice looking receipt
    conn = get_db()
    c = conn.cursor()
    
    # fetch the header
    c.execute('SELECT customer_id, posting_date, grand_total FROM tabSalesInvoice WHERE invoice_id = ?', (invoice_id,))
    header = c.fetchone()
    if not header:
        print(f"Invoice {invoice_id} not found!")
        return
        
    c_id, date, total = header
    
    # fetch customer name
    c.execute('SELECT customer_name FROM tabCustomer WHERE customer_id = ?', (c_id,))
    cust = c.fetchone()
    cust_name = cust[0] if cust else c_id
    
    # fetch the line items
    c.execute('SELECT item_code, qty, rate, amount FROM tabInvoiceItem WHERE parent_id = ?', (invoice_id,))
    lines = c.fetchall()
    
    print("\n" + "="*40)
    print("           QUICKSTOCK RECEIPT           ")
    print("="*40)
    print(f"Invoice ID: {invoice_id}")
    print(f"Date:       {date}")
    print(f"Customer:   {cust_name}")
    print("-" * 40)
    print(f"{'Item':<15} {'Qty':<5} {'Rate':<8} {'Amount'}")
    print("-" * 40)
    for line in lines:
        print(f"{line[0]:<15} {line[1]:<5} ${line[2]:<7.2f} ${line[3]:.2f}")
    print("-" * 40)
    print(f"{'GRAND TOTAL:':<30} ${total:.2f}")
    print("="*40 + "\n")
    
    conn.close()

# couple of quick helpers to seed data for testing
def add_item(code, name, rate, stock):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO tabItem (item_code, item_name, valuation_rate, opening_stock)
        VALUES (?, ?, ?, ?)
    ''', (code, name, rate, stock))
    conn.commit()
    conn.close()

def add_customer(cid, name, email):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO tabCustomer (customer_id, customer_name, email)
        VALUES (?, ?, ?)
    ''', (cid, name, email))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # test script below
    init_db()
    print("db ready")
    
    add_item("ITEM-001", "Macbook", 1200.0, 100)
    add_item("ITEM-002", "Logitech Mouse", 25.0, 100)
    add_customer("CUST-001", "Priyanka Limbad", "priya@test.com")
    
    print("ITEM-001 stock before:", check_stock('ITEM-001'))
    print("ITEM-002 stock before:", check_stock('ITEM-002'))
    
    # normal order
    cart = [
        {'item_code': 'ITEM-001', 'qty': 5, 'rate': 1200.0},
        {'item_code': 'ITEM-002', 'qty': 5, 'rate': 25.0}
    ]
    
    try:
        new_inv = create_invoice("CUST-001", cart)
        print("created invoice:", new_inv)
        print_receipt(new_inv)
    except Exception as e:
        pass
        
    print("ITEM-001 stock after:", check_stock('ITEM-001'))
    print("ITEM-002 stock after:", check_stock('ITEM-002'))
    
    # testing the validation logic
    huge_order = [
        {'item_code': 'ITEM-001', 'qty': 50, 'rate': 1200.0},
        {'item_code': 'ITEM-002', 'qty': 50, 'rate': 25.0}
    ]
    
    print("\n--- testing rollback on huge order ---")
    try:
        huge_inv = create_invoice("CUST-001", huge_order)
        print("created massive invoice successfully!")
        print_receipt(huge_inv)
    except Exception as e:
        print("caught error perfectly:", e)
