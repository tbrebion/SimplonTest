from flask import Flask, render_template, jsonify
import sqlite3
import re

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('/app/db/database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    sales = conn.execute('SELECT * FROM sales').fetchall()
    products = conn.execute('SELECT * FROM products').fetchall()
    stores = conn.execute('SELECT * FROM stores').fetchall()
    analysis_results = conn.execute('SELECT * FROM analysis_results').fetchall()
    
    # Prepare data for pie charts
    product_sales_data = []
    region_sales_data = []
    
    for result in analysis_results:
        if result['metric'] == 'total_revenue':
            total_revenue = result['value']
        elif result['metric'].startswith('sales_product_'):
            product_id = result['metric'].replace('sales_product_', '')
            # Get product name if available
            product = conn.execute('SELECT name FROM products WHERE product_id = ?', (product_id,)).fetchone()
            product_name = product['name'] if product else f"Product {product_id}"
            product_sales_data.append({
                'label': product_name,
                'value': result['value']
            })
        elif result['metric'].startswith('sales_region_'):
            region = result['metric'].replace('sales_region_', '')
            region_sales_data.append({
                'label': region,
                'value': result['value']
            })
    
    conn.close()
    
    return render_template('index.html', 
                          sales=sales, 
                          products=products, 
                          stores=stores, 
                          analysis_results=analysis_results,
                          product_sales_data=product_sales_data,
                          region_sales_data=region_sales_data)

@app.route('/api/chart-data')
def chart_data():
    conn = get_db_connection()
    
    # Product sales data
    product_sales = []
    product_results = conn.execute('SELECT * FROM analysis_results WHERE metric LIKE "sales_product_%"').fetchall()
    for result in product_results:
        product_id = result['metric'].replace('sales_product_', '')
        product = conn.execute('SELECT name FROM products WHERE product_id = ?', (product_id,)).fetchone()
        product_name = product['name'] if product else f"Product {product_id}"
        product_sales.append({
            'label': product_name,
            'value': result['value']
        })
    
    # Region sales data
    region_sales = []
    region_results = conn.execute('SELECT * FROM analysis_results WHERE metric LIKE "sales_region_%"').fetchall()
    for result in region_results:
        region = result['metric'].replace('sales_region_', '')
        region_sales.append({
            'label': region,
            'value': result['value']
        })
    
    conn.close()
    
    return jsonify({
        'product_sales': product_sales,
        'region_sales': region_sales
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)