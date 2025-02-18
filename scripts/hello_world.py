import sqlite3
import pandas as pd
import requests
import io

try:
    conn = sqlite3.connect('/app/db/database.db')
    print("Successfully connected to database")
except Exception as e:
    print("Error connecting to database:", str(e))
    raise e
cursor = conn.cursor()

# Create tables if they don't exist with proper foreign key relationships
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    number_of_employees INTEGER NOT NULL CHECK (number_of_employees >= 0)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS sales (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    store_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

def import_data_from_url(url, table_name, column_mapping, dtype_mapping):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Read CSV data from the response content
        csv_data = io.StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        df.rename(columns=column_mapping, inplace=True)
        df = df.astype(dtype_mapping)
        
        if table_name in ['products', 'stores']:
            # For products and stores, only insert if they don't exist
            existing_ids = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            if not existing_ids.empty:
                print(f"Table {table_name} already has data, skipping import")
                return
                
        elif table_name == 'sales':
            # For sales, clear existing data before inserting new
            cursor.execute('DELETE FROM sales')
            
            # Generate a unique ID for each sale if it doesn't exist
            if 'id' not in df.columns:
                df['id'] = [f"SALE_{i}" for i in range(len(df))]
            
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"Successfully imported data for {table_name}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL for {table_name}: {str(e)}")
    except Exception as e:
        print(f"Error processing data for {table_name}: {str(e)}")

# Define URLs
products_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSawI56WBC64foMT9pKCiY594fBZk9Lyj8_bxfgmq-8ck_jw1Z49qDeMatCWqBxehEVoM6U1zdYx73V/pub?gid=0&single=true&output=csv"
stores_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSawI56WBC64foMT9pKCiY594fBZk9Lyj8_bxfgmq-8ck_jw1Z49qDeMatCWqBxehEVoM6U1zdYx73V/pub?gid=714623615&single=true&output=csv"
sales_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSawI56WBC64foMT9pKCiY594fBZk9Lyj8_bxfgmq-8ck_jw1Z49qDeMatCWqBxehEVoM6U1zdYx73V/pub?gid=760830694&single=true&output=csv"

sales_column_mapping = {
    'Date': 'date',
    'ID Référence produit': 'product_id',
    'Quantité': 'amount',
    'ID Magasin': 'store_id'
}

sales_dtype_mapping = {
    'date': str,
    'product_id': str,
    'amount': int,
    'store_id': int
}

products_column_mapping = {
    'Nom': 'name',
    'ID Référence produit': 'product_id',
    'Prix': 'price',
    'Stock': 'stock'
}

products_dtype_mapping = {
    'name': str,
    'product_id': str,
    'price': float,
    'stock': int
}

stores_column_mapping = {
    'ID Magasin': 'id',
    'Ville': 'city',
    'Nombre de salariés': 'number_of_employees'
}

stores_dtype_mapping = {
    'id': int,
    'city': str,
    'number_of_employees': int
}

# Import data with HTTP requests
import_data_from_url(products_url, 'products', products_column_mapping, products_dtype_mapping)
import_data_from_url(stores_url, 'stores', stores_column_mapping, stores_dtype_mapping)
import_data_from_url(sales_url, 'sales', sales_column_mapping, sales_dtype_mapping)

# Clear existing analysis results before new calculation
cursor.execute('DELETE FROM analysis_results')

# Calculate sales by product
cursor.execute('''
SELECT product_id, SUM(amount) FROM sales GROUP BY product_id
''')
sales_by_product = cursor.fetchall()

cursor.execute('''
SELECT product_id, price FROM products
''')
price_by_product = cursor.fetchall()

price_dict = {product_id: price for product_id, price in price_by_product}

result = {product_id: total_sales * price_dict.get(product_id, 0) for product_id, total_sales in sales_by_product}

# Calculate sales by region with proper joins
cursor.execute('''
SELECT stores.city, SUM(sales.amount * products.price) AS total_revenue
FROM sales
JOIN stores ON sales.store_id = stores.id
JOIN products ON sales.product_id = products.product_id
GROUP BY stores.city
''')
sales_by_region = cursor.fetchall()

total = sum(result.values())

# Insert new analysis results
cursor.execute('''
INSERT INTO analysis_results (metric, value) VALUES (?, ?)
''', ('total_revenue', total))

for product_id, value in result.items():
    cursor.execute('''
    INSERT INTO analysis_results (metric, value) VALUES (?, ?)
    ''', (f'sales_product_{product_id}', value))

for city, amount in sales_by_region:
    cursor.execute('''
    INSERT INTO analysis_results (metric, value) VALUES (?, ?)
    ''', (f'sales_region_{city}', amount))

conn.commit()
conn.close()