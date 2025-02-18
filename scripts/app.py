from flask import Flask, render_template
import sqlite3

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
    conn.close()
    return render_template('index.html', sales=sales, products=products, stores=stores, analysis_results=analysis_results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
