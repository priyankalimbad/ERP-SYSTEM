import sqlite3
import uuid
from datetime import date

DB_NAME = 'quickstock.db'

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)

def setup_database():
    """Creates the necessary tables for the QuickStock ERP system."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create tabItem table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tabItem (
        item_code TEXT PRIMARY KEY,
        item_name TEXT,
        valuation_rate REAL,
        opening_stock INTEGER
    )
    ''')
    
    # Create tabCustomer table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tabCustomer (
        customer_id TEXT PRIMARY KEY,
        customer_name TEXT,
        email TEXT
    )
    ''')
    
    # Create tabSalesInvoice table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tabSalesInvoice (
        invoice_id TEXT PRIMARY KEY,
        customer_id TEXT,
        posting_date TEXT,
        grand_total REAL,
        FOREIGN KEY (customer_id) REFERENCES tabCustomer (customer_id)
    )
    ''')
    
    # Create tabInvoiceItem table
    cursor.execute('''
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
    """
    Calculates the total price, inserts the main invoice, 
    and then inserts each item into the tabInvoiceItem table.
    
    Args:
        customer_id (str): The ID of the customer.
        items_list (list of dict): List of items where each dictionary contains 
                                   'item_code', 'qty', and 'rate'.
                                   
    Returns:
        str: The generated invoice_id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate grand total and prepare item details
        grand_total = 0
        invoice_items = []
        for item in items_list:
            amount = item['qty'] * item['rate']
            grand_total += amount
            invoice_items.append({
                'item_code': item['item_code'],
                'qty': item['qty'],
                'rate': item['rate'],
                'amount': amount
            })
            
        # Generate a unique Invoice ID and get current date
        invoice_id = "INV-" + str(uuid.uuid4())[:8].upper()
        posting_date = date.today().isoformat()
        
        # Insert into tabSalesInvoice
        cursor.execute('''
        INSERT INTO tabSalesInvoice (invoice_id, customer_id, posting_date, grand_total)
        VALUES (?, ?, ?, ?)
        ''', (invoice_id, customer_id, posting_date, grand_total))
        
        # Insert into tabInvoiceItem
        for item in invoice_items:
            cursor.execute('''
            INSERT INTO tabInvoiceItem (parent_id, item_code, qty, rate, amount)
            VALUES (?, ?, ?, ?, ?)
            ''', (invoice_id, item['item_code'], item['qty'], item['rate'], item['amount']))
            
        conn.commit()
        return invoice_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating invoice: {e}")
        raise
    finally:
        conn.close()

def check_stock(item_code):
    """
    Calculates current stock by taking opening_stock minus 
    the total qty sold in tabInvoiceItem.
    
    Args:
        item_code (str): The item code to check.
        
    Returns:
        int: The current stock available.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get opening stock
    cursor.execute('''
    SELECT opening_stock FROM tabItem WHERE item_code = ?
    ''', (item_code,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise ValueError(f"Item {item_code} not found in database.")
        
    opening_stock = result[0]
    
    # Get total quantity sold
    cursor.execute('''
    SELECT SUM(qty) FROM tabInvoiceItem WHERE item_code = ?
    ''', (item_code,))
    sales_result = cursor.fetchone()
    
    total_qty_sold = sales_result[0] if sales_result[0] is not None else 0
    current_stock = opening_stock - total_qty_sold
    
    conn.close()
    return current_stock

# Helper functions for adding base data
def add_item(item_code, item_name, valuation_rate, opening_stock):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO tabItem (item_code, item_name, valuation_rate, opening_stock)
    VALUES (?, ?, ?, ?)
    ''', (item_code, item_name, valuation_rate, opening_stock))
    conn.commit()
    conn.close()

def add_customer(customer_id, customer_name, email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO tabCustomer (customer_id, customer_name, email)
    VALUES (?, ?, ?)
    ''', (customer_id, customer_name, email))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Initialize the database and tables
    setup_database()
    print("Database setup complete.")
    
    # Add some sample data for testing
    add_item("ITEM-001", "Laptop", 800.0, 50)
    add_item("ITEM-002", "Wireless Mouse", 20.0, 200)
    add_customer("CUST-001", "Alice Smith", "alice@example.com")
    
    print("\n--- Initial Stock ---")
    print(f"ITEM-001 Stock: {check_stock('ITEM-001')}")
    print(f"ITEM-002 Stock: {check_stock('ITEM-002')}")
    
    # Create a test invoice
    items_to_buy = [
        {'item_code': 'ITEM-001', 'qty': 2, 'rate': 1000.0},
        {'item_code': 'ITEM-002', 'qty': 5, 'rate': 25.0}
    ]
    
    print("\n--- Creating Invoice ---")
    try:
        inv_id = create_invoice("CUST-001", items_to_buy)
        print(f"Successfully created Invoice: {inv_id}")
    except Exception as e:
        print(f"Failed to create invoice. Error: {e}")
    
    print("\n--- Stock After Sale ---")
    print(f"ITEM-001 Stock: {check_stock('ITEM-001')}")
    print(f"ITEM-002 Stock: {check_stock('ITEM-002')}")
