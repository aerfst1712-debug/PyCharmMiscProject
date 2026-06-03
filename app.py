import os
from flask import Flask, render_template, request, redirect, jsonify, session
import sqlite3
from datetime import datetime
import
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'electrohub_secret_key_1234'

# ตั้งค่าโฟลเดอร์สำหรับเก็บไฟล์สลิปโอนเงิน
UPLOAD_FOLDER = 'static/slips'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db():
    conn = sqlite3.connect('electronics.db')
    conn.row_factory = sqlite3.Row
    return conn

def update_db_structure():
    conn = get_db()
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT "ยังไม่เลือกช่องทาง"')
    except:
        pass
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT "รอดำเนินการ"')
    except:
        pass
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN slip_image TEXT DEFAULT NULL')
    except:
        pass
    # 1. ตารางสินค้าหลัก
    conn.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            image_url TEXT
        )
    ''')
    # 2. ตาราง Logs กิจกรรม
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_name TEXT NOT NULL,
            action_type TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    # 3. ตารางประวัติใบสั่งซื้อหลัก (เพิ่มฟิลด์สถานะและการจ่ายเงินสำหรับ Hybrid Checkout)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            payment_method TEXT DEFAULT 'ยังไม่เลือกช่องทาง',
            payment_status TEXT DEFAULT 'รอดำเนินการ',
            slip_image TEXT DEFAULT NULL
        )
    ''')
    # 4. ตารางรายการสินค้าในแต่ละใบสั่งซื้อ
    conn.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            component_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_piece INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')
    conn.commit()
    conn.close()

# รันเพื่อตรวจสอบตารางทุกครั้งที่เปิดโปรแกรม
update_db_structure()

@app.route('/')
def index():
    is_admin = session.get('is_admin', False)
    search_query = request.args.get('search', '')
    current_category = request.args.get('category', '')

    conn = get_db()

    # ดึงหมวดหมู่ทั้งหมดสำหรับทำปุ่มตัวกรอง
    categories_res = conn.execute('SELECT DISTINCT category FROM components').fetchall()
    categories = [row['category'] for row in categories_res]

    # สร้าง SQL Query ตามการค้นหาและการกรองหมวดหมู่
    query = 'SELECT * FROM components WHERE 1=1'
    params = []

    if search_query:
        query += ' AND (name LIKE ? OR description LIKE ? OR category LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    if current_category:
        query += ' AND category = ?'
        params.append(current_category)

    products = conn.execute(query, params).fetchall()

    # คำนวณตัวเลขแผง Dashboard
    total_items = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0] or 0
    total_stock = conn.execute('SELECT SUM(stock) FROM components').fetchone()[0] or 0
    low_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock > 0 AND stock < 15').fetchone()[0] or 0
    out_of_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock = 0').fetchone()[0] or 0

    value_res = conn.execute('SELECT SUM(stock * price) FROM components').fetchone()[0]
    total_warehouse_value = value_res or 0

    # ดึงประวัติใบสั่งซื้อล่าสุด 6 รายการ และ Logs ล่าสุด 8 รายการ
    recent_orders = conn.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 6').fetchall()
    logs = conn.execute('SELECT * FROM stock_logs ORDER BY id DESC LIMIT 8').fetchall()

    conn.close()

    return render_template('index.html', products=products, categories=categories,
                           current_category=current_category, search_query=search_query,
                           total_items=total_items, total_stock=total_stock,
                           low_stock_count=low_stock_count, out_of_stock_count=out_of_stock_count,
                           total_warehouse_value=total_warehouse_value, recent_orders=recent_orders,
                           logs=logs, is_admin=is_admin)

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    if not data or 'cart' not in data or len(data['cart']) == 0:
        return jsonify({'success': False, 'message': 'ไม่มีสินค้าในตะกร้า'})

    conn = get_db()
    cart = data['cart']

    # 1. ตรวจสอบสต็อกสินค้าทั้งหมดก่อนตัดจริง
    for item in cart:
        prod = conn.execute('SELECT * FROM components WHERE id = ?', (item['id'],)).fetchone()
        if not prod:
            conn.close()
            return jsonify({'success': False, 'message': f'ไม่พบชิ้นส่วนรหัส {item["id"]} ในระบบ'})
        if prod['stock'] < int(item['qty']):
            conn.close()
            return jsonify({'success': False, 'message': f'สินค้า {prod["name"]} มีสต็อกไม่พอ (เหลือ {prod["stock"]} ชิ้น)'})

    # 2. บันทึกข้อมูลลงตารางใบสั่งซื้อหลัก
    order_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    total_price = sum(int(item['price']) * int(item['qty']) for item in cart)

    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (order_date, total_price, payment_method, payment_status) VALUES (?, ?, ?, ?)',
                   (order_date, total_price, 'ยังไม่เลือกช่องทาง', 'รอดำเนินการ'))
    order_id = cursor.lastrowid

    # 3. หักสต็อกสินค้าจริง และบันทึกรายการสินค้าของบิลนั้นๆ พร้อมลงบันทึกกิจกรรม (Logs)
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    for item in cart:
        qty = int(item['qty'])
        conn.execute('UPDATE components SET stock = stock - ? WHERE id = ?', (qty, item['id']))
        conn.execute('INSERT INTO order_items (order_id, component_id, component_name, quantity, price_per_piece) VALUES (?, ?, ?, ?, ?)',
                     (order_id, item['id'], item['name'], qty, item['price']))
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (item['name'], f'📉 ถูกเบิกจำนวน {qty} ชิ้น (บิล #{order_id})', now_str))

    conn.commit()
    conn.close()

    # ส่ง order_id กลับไปเพื่อให้ Javascript พาวาร์ปไปหน้าตรวจสอบการชำระเงิน
    return jsonify({'success': True, 'message': 'บันทึกคำสั่งซื้อเรียบร้อย!', 'order_id': order_id})

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order:
        conn.close()
        return "ไม่พบใบสั่งซื้อนี้ในระบบ", 404

    items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
    conn.close()
    return render_template('order.html', order=order, items=items)

@app.route('/order/<int:order_id>/update_payment', methods=['POST'])
def update_payment(order_id):
    method = request.form.get('payment_method')
    status = 'รอดำเนินการ'
    slip_filename = None

    if method == 'cash_on_pickup':
        method_th = 'จ่ายเงินสดตอนมารับของ'
        status = 'ชำระเงินหน้าร้าน'
    elif method == 'qr_now':
        method_th = 'โอนเงินผ่าน QR Code'
        status = 'ชำระเงินสำเร็จ (QR)'
    elif method == 'upload_slip':
        method_th = 'โอนเงินแบบ Manual (แนบสลิป)'
        file = request.files.get('slip_image')
        if file and file.filename != '':
            filename = secure_filename(f"order_{order_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            slip_filename = f"/static/slips/{filename}"
            status = 'รอตรวจสอบสลิป'
    else:
        return redirect(f'/order/{order_id}')

    conn = get_db()
    if slip_filename:
        conn.execute('UPDATE orders SET payment_method=?, payment_status=?, slip_image=? WHERE id=?',
                     (method_th, status, slip_filename, order_id))
    else:
        conn.execute('UPDATE orders SET payment_method=?, payment_status=? WHERE id=?',
                     (method_th, status, order_id))

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                 (f'บิลออเดอร์ #{order_id}', f'💳 อัปเดตการชำระเงิน: {method_th} [สถานะ: {status}]', now_str))

    conn.commit()
    conn.close()
    return redirect(f'/order/{order_id}')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    if password == '1234':
        session['is_admin'] = True
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect('/')

# หมายเหตุ: สำหรับฟังก์ชันเบื้องต้นอื่นๆ (add, edit, delete, update_stock) ให้คงไว้ตามโครงสร้างเดิมของคุณได้เลยครับ
if __name__ == '__main__':
    app.run(debug=True)