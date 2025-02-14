import sqlite3
import pandas as pd


try:
    conn = sqlite3.connect('/app/db/database.db')
    print("Successfully connected to database")
except Exception as e:
    print("Error connecting to database:", str(e))
    raise e
cursor = conn.cursor()


cursor.execute('DROP TABLE IF EXISTS sales')
cursor.execute('DROP TABLE IF EXISTS products')
cursor.execute('DROP TABLE IF EXISTS stores')
cursor.execute('DROP TABLE IF EXISTS analysis_results')


cursor.execute('''
CREATE TABLE IF NOT EXISTS sales (
    id TEXT PRIMARY KEY,
    product_id TEXT,
    store_id INTEGER,
    date TEXT,
    amount REAL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    product_id TEXT,
    name TEXT,
    price REAL,
	stock INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY,
    city TEXT,
    number_of_employees INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY,
    metric TEXT,
    value REAL
)
''')

conn.commit()



def import_data_from_csv(file_path, table_name, column_mapping, dtype_mapping):
    df = pd.read_csv(file_path)
    df.rename(columns=column_mapping, inplace=True)
    df = df.astype(dtype_mapping)
    df.to_sql(table_name, conn, if_exists='append', index=False)



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

import_data_from_csv('/app/data/sales.csv', 'sales', sales_column_mapping, sales_dtype_mapping)
import_data_from_csv('/app/data/products.csv', 'products', products_column_mapping, products_dtype_mapping)
import_data_from_csv('/app/data/stores.csv', 'stores', stores_column_mapping, stores_dtype_mapping)


cursor.execute('''
SELECT product_id, SUM(amount) FROM sales GROUP BY product_id
''')
sales_by_product = cursor.fetchall()

cursor.execute('''
SELECT product_id, price FROM products
''')
price_by_product = cursor.fetchall()

price_dict = {product_id: price for product_id, price in price_by_product}

result = {product_id: total_sales * price_dict[product_id] for product_id, total_sales in sales_by_product}

cursor.execute('''
SELECT stores.city, SUM(sales.amount * products.price) AS total_revenue
FROM sales
JOIN stores ON sales.store_id = stores.id
JOIN products ON sales.product_id = products.product_id
GROUP BY stores.city
''')
sales_by_region = cursor.fetchall()


total = sum(result.values())

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
