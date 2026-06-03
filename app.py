from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash, Response
import sqlite3
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'electrohub_labs_secret_key_2024'

DATABASE = 'electronics.db'
ADMIN_PASSWORD = '1234'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def update_db_structure():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS components
                    (
                        id
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        name
                        TEXT
                        NOT
                        NULL,
                        category
                        TEXT
                        NOT
                        NULL,
                        price
                        TEXT
                        NOT
                        NULL,
                        image_url
                        TEXT,
                        description
                        TEXT,
                        specs
                        TEXT,
                        stock
                        INTEGER
                        DEFAULT
                        0,
                        datasheet_url
                        TEXT
                    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stock_logs
                    (
                        id
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        component_name
                        TEXT
                        NOT
                        NULL,
                        action_type
                        TEXT
                        NOT
                        NULL,
                        timestamp
                        TEXT
                        NOT
                        NULL
                    )''')
    conn.commit()
    cursor = conn.execute('SELECT COUNT(*) FROM components')
    if cursor.fetchone()[0] == 0:
        default_components = [
            ('IC LM358', 'Integrated Circuit', '50 บาท', 'https://th.rs-online.com/images/F4852924-01.jpg',
             'ไอซีขยายสัญญาณ Low Power Dual Operational Amplifier', 'ขาใช้งาน: 8 พิน, แรงดันไฟเลี้ยง: 3V-32V', 100,
             'https://www.ti.com/lit/ds/symlink/lm358.pdf'),
            ('Arduino Uno R3', 'Microcontroller', '250 บาท',
             'https://docs.arduino.cc/static/29849b29d499ec249f056bc293d07ec5/A000066_featured.jpg',
             'บอร์ดไมโครคอนโทรลเลอร์ยอดนิยม', 'ชิปหลัก: ATmega328P, แรงดัน: 5V', 12,
             'https://docs.arduino.cc/resources/datasheets/A000066-datasheet-pdf')
        ]
        conn.executemany(
            'INSERT INTO components (name, category, price, image_url, description, specs, stock, datasheet_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            default_components)
        conn.commit()
    conn.close()


@app.route('/')
def home():
    is_admin = session.get('is_admin') == True
    search_query = request.args.get('search', '').strip()
    conn = get_db()

    if search_query:
        cursor = conn.execute("SELECT * FROM components WHERE name LIKE ?", (f"%{search_query}%",))
    else:
        cursor = conn.execute('SELECT * FROM components')

    products = [dict(row) for row in cursor.fetchall()]
    total_items = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0]
    total_stock = conn.execute('SELECT SUM(stock) FROM components').fetchone()[0] or 0
    low_stock = conn.execute('SELECT COUNT(*) FROM components WHERE stock < 5 AND stock > 0').fetchone()[0]
    out_stock = conn.execute('SELECT COUNT(*) FROM components WHERE stock == 0').fetchone()[0]

    chart_cursor = conn.execute('SELECT category, SUM(stock) as s FROM components GROUP BY category')
    chart_labels = []
    chart_data = []
    for r in chart_cursor:
        chart_labels.append(r['category'])
        chart_data.append(r['s'] or 0)

    logs = conn.execute('SELECT * FROM stock_logs ORDER BY id DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('index.html', products=products, is_admin=is_admin, total_items=total_items,
                           total_stock=total_stock, low_stock_count=low_stock, out_of_stock_count=out_stock,
                           chart_labels=chart_labels, chart_data=chart_data, logs=logs)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('home'))
        flash('รหัสผ่านไม่ถูกต้อง!', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))


@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart = data.get('cart', [])
    conn = get_db()
    order_id = "ORD-" + datetime.now().strftime('%Y%m%d%H%M%S')
    for item in cart:
        conn.execute('UPDATE components SET stock = stock - ? WHERE id = ?', (item['qty'], item['id']))
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (item['name'], f"เบิกจ่าย {item['qty']} ชิ้น (Order: {order_id})",
                      datetime.now().strftime('%H:%M:%S')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'order_id': order_id})


@app.route('/receipt/<order_id>')
def receipt(order_id):
    return render_template('receipt.html', order_id=order_id)


# (ก๊อปปี้รูท /add, /edit, /delete จากโค้ดเดิมของคุณมาใส่ตรงนี้)

if __name__ == '__main__':
    update_db_structure()
    app.run(debug=True)


    @app.route('/admin-login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['is_admin'] = True
                return redirect(url_for('home'))
            flash('รหัสผ่านไม่ถูกต้อง!', 'danger')
        return render_template('login.html')