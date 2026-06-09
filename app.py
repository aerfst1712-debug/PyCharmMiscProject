from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, Response
import sqlite3
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'electrohub_labs_super_secret_key_999'

DATABASE = 'electronics.db'
ADMIN_PASSWORD = '1234'  # รหัสผ่านหลักของแอดมิน


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def update_db_structure():
    conn = get_db()
    try:
        conn.execute("ALTER TABLE components ADD COLUMN stock INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE components ADD COLUMN datasheet_url TEXT")
    except sqlite3.OperationalError:
        pass

    # สร้างตารางประวัติกิจกรรมสต็อก
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS stock_logs
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
                 )
                 ''')

    # ✨ สร้างตารางบิลคำสั่งซื้อ/ใบเบิกคลัง เพื่อรองรับโค้ดบนหน้า HTML
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS orders
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     total_price
                     INTEGER
                     NOT
                     NULL,
                     order_date
                     TEXT
                     NOT
                     NULL,
                     items_json
                     TEXT
                     NOT
                     NULL
                 )
                 ''')
    conn.commit()

    cursor = conn.execute('SELECT COUNT(*) FROM components')
    if cursor.fetchone()[0] == 0:
        default_components = [
            ('IC LM358', 'Integrated Circuit', '50 บาท', 'https://th.rs-online.com/images/F4852924-01.jpg',
             'ไอซีขยายสัญญาณ Low Power Dual Operational Amplifier นิยมใช้ในวงจรกรองสัญญาณและวงจรเปรียบเทียบแรงดัน',
             'ขาใช้งาน: 8 พิน, แรงดันไฟเลี้ยง: 3V ถึง 32V, จำนวนช่องสัญญาณ: 2 ช่อง', 100,
             'https://www.ti.com/lit/ds/symlink/lm358.pdf'),
            ('Arduino Uno R3', 'Microcontroller', '250 บาท',
             'https://docs.arduino.cc/static/29849b29d499ec249f056bc293d07ec5/A000066_featured.jpg',
             'บอร์ดไมโครคอนโทรลเลอร์โอเพนซอร์สยอดนิยมสำหรับเรียนรู้และพัฒนาระบบฝังตัว วงจรอิเล็กทรอนิกส์ และหุ่นยนต์',
             'ชิปหลัก: ATmega328P, แรงดันใช้งาน: 5V, ขา Digital I/O: 14 ขา, ขา Analog Input: 6 ขา', 4,
             'https://docs.arduino.cc/resources/datasheets/A000066-datasheet-pdf')
        ]

        # แปลงโครงสร้างราคาให้เป็นตัวเลขเพียวๆ เพื่อนำไปคำนวณมูลค่าคลังสินค้าได้
        clean_components = [
            ('IC LM358', 'Integrated Circuit', '50', 'https://th.rs-online.com/images/F4852924-01.jpg',
             'ไอซีขยายสัญญาณ Low Power Dual Operational Amplifier นิยมใช้ในวงจรกรองสัญญาณและวงจรเปรียบเทียบแรงดัน',
             'ขาใช้งาน: 8 พิน, แรงดันไฟเลี้ยง: 3V ถึง 32V, จำนวนช่องสัญญาณ: 2 ช่อง', 100,
             'https://www.ti.com/lit/ds/symlink/lm358.pdf'),
            ('Arduino Uno R3', 'Microcontroller', '250',
             'https://docs.arduino.cc/static/29849b29d499ec249f056bc293d07ec5/A000066_featured.jpg',
             'บอร์ดไมโครคอนโทรลเลอร์โอเพนซอร์สยอดนิยมสำหรับเรียนรู้และพัฒนาระบบฝังตัว วงจรอิเล็กทรอนิกส์ และหุ่นยนต์',
             'ชิปหลัก: ATmega328P, แรงดันใช้งาน: 5V, ขา Digital I/O: 14 ขา, ขา Analog Input: 6 ขา', 4,
             'https://docs.arduino.cc/resources/datasheets/A000066-datasheet-pdf')
        ]
        conn.executemany('''
                         INSERT INTO components (name, category, price, image_url, description, specs, stock,
                                                 datasheet_url)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         ''', clean_components)
        conn.commit()
    conn.close()


def is_logged_in_admin():
    return session.get('is_admin') == True


@app.route('/')
def home():
    is_admin = is_logged_in_admin()
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    conn = get_db()
    cat_cursor = conn.execute('SELECT DISTINCT category FROM components')
    categories = [row['category'] for row in cat_cursor.fetchall()]

    if search_query:
        query = "SELECT * FROM components WHERE name LIKE ? OR category LIKE ?"
        cursor = conn.execute(query, (f"%{search_query}%", f"%{search_query}%"))
    elif category_filter:
        query = "SELECT * FROM components WHERE category = ?"
        cursor = conn.execute(query, (category_filter,))
    else:
        cursor = conn.execute('SELECT * FROM components')

    products = [dict(row) for row in cursor.fetchall()]

    # ✨ ปรับปรุงให้มีตัวแปรเริ่มต้นสถิติต่างๆ ครบถ้วน ป้องกัน Jinja2 แสดงผลผิดพลาด
    total_items = 0
    total_stock = 0
    total_warehouse_value = 0
    low_stock_count = 0
    out_of_stock_count = 0
    logs = []
    recent_orders = []

    try:
        total_items = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0] or 0
        total_stock_res = conn.execute('SELECT SUM(stock) FROM components').fetchone()[0]
        total_stock = total_stock_res if total_stock_res is not None else 0
        low_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock < 5 AND stock > 0').fetchone()[
                              0] or 0
        out_of_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock == 0').fetchone()[0] or 0

        # ✨ ฟังก์ชันคำนวณมูลค่าสินค้ารวมทั้งหมดในโกดัง (ราคาชิ้นส่วน x จำนวนชิ้นในสต็อก)
        all_comps = conn.execute('SELECT price, stock FROM components').fetchall()
        for comp in all_comps:
            try:
                # ล้างอักขระที่ไม่ใช่ตัวเลขออกเผื่อมีการใส่คำว่า "บาท" ไว้ในตัวฐานข้อมูลเก่า
                price_clean = ''.join(c for c in str(comp['price']) if c.isdigit() or c == '.')
                price_val = float(price_clean) if price_clean else 0.0
                total_warehouse_value += int(price_val * (comp['stock'] or 0))
            except ValueError:
                pass

        if is_admin:
            log_cursor = conn.execute('SELECT * FROM stock_logs ORDER BY id DESC LIMIT 10')
            logs = log_cursor.fetchall()

            # ดึงประวัติใบเบิกคลังล่าสุดมาแสดงผล
            order_cursor = conn.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 10')
            recent_orders = order_cursor.fetchall()

    except sqlite3.OperationalError:
        pass

    conn.close()
    return render_template('index.html',
                           products=products,
                           is_admin=is_admin,
                           search_query=search_query,
                           categories=categories,
                           current_category=category_filter,
                           total_items=total_items,
                           total_stock=total_stock,
                           total_warehouse_value=total_warehouse_value,  # ✨ ส่งตัวแปรมูลค่าคลังสินค้าไปที่หน้าจอ
                           low_stock_count=low_stock_count,
                           out_of_stock_count=out_of_stock_count,
                           logs=logs,
                           recent_orders=recent_orders)  # ✨ ส่งข้อมูลประวัติบิล


@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))


@app.route('/update_stock/<int:product_id>/<string:action>')
def update_stock(product_id, action):
    if not is_logged_in_admin(): return abort(403)

    conn = get_db()
    comp = conn.execute('SELECT name, stock FROM components WHERE id = ?', (product_id,)).fetchone()

    if comp:
        current_stock = comp['stock'] or 0
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        if action == 'increase':
            conn.execute('UPDATE components SET stock = stock + 1 WHERE id = ?', (product_id,))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (comp['name'], f'➕ ปรับเพิ่มสต็อกด่วนเป็น {current_stock + 1} ชิ้น', now_str))
        elif action == 'decrease' and current_stock > 0:
            conn.execute('UPDATE components SET stock = MAX(0, stock - 1) WHERE id = ?', (product_id,))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (comp['name'], f'➖ ปรับลดสต็อกด่วนเหลือ {current_stock - 1} ชิ้น', now_str))
        conn.commit()
    conn.close()
    return redirect(url_for('home'))


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,)).fetchone()
    conn.close()

    if product is None: abort(404)

    product_dict = dict(product)
    product_dict['specs'] = [s.strip() for s in product_dict['specs'].split(',')] if product_dict['specs'] else []
    return render_template('product.html', product=product_dict, is_admin=is_logged_in_admin())


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if not is_logged_in_admin(): return abort(403)

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']

        try:
            stock = int(request.form.get('stock', 0))
            if stock < 0: stock = 0
        except ValueError:
            stock = 0

        datasheet_url = request.form.get('datasheet_url', '')

        conn = get_db()
        conn.execute('''
                     INSERT INTO components (name, category, price, image_url, description, specs, stock, datasheet_url)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                     ''', (name, category, price, image_url, description, specs, stock, datasheet_url))

        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (name, '🆕 เพิ่มอุปกรณ์ใหม่เข้าสู่ระบบคลังชิ้นส่วน', now_str))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    return render_template('add.html', is_admin=True)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not is_logged_in_admin(): return abort(403)

    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']

        try:
            stock = int(request.form.get('stock', 0))
            if stock < 0: stock = 0
        except ValueError:
            stock = 0

        datasheet_url = request.form.get('datasheet_url', '')

        conn.execute('''
                     UPDATE components
                     SET name=?,
                         category=?,
                         price=?,
                         image_url=?,
                         description=?,
                         specs=?,
                         stock=?,
                         datasheet_url=?
                     WHERE id = ?
                     ''', (name, category, price, image_url, description, specs, stock, datasheet_url, product_id))

        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (name, '✏️ แก้ไขอัปเดตข้อมูลรายละเอียดชิ้นส่วน', now_str))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    product = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return render_template('edit.html', product=product, is_admin=True)


@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    if not is_logged_in_admin(): return abort(403)

    conn = get_db()
    comp = conn.execute('SELECT name FROM components WHERE id = ?', (product_id,)).fetchone()
    if comp:
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (comp['name'], '🗑️ ลบอุปกรณ์เบอร์นี้ออกจากคลังข้อมูล', now_str))
        conn.execute('DELETE FROM components WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))


@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart_items = data.get('cart', [])
    if not cart_items: return jsonify({'success': False, 'message': 'ไม่มีสินค้าในตะกร้า'}), 400

    conn = get_db()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    total_bill_price = 0
    import json

    try:
        for item in cart_items:
            product_id = item.get('id')
            qty = int(item.get('qty', 1))

            db_item = conn.execute('SELECT name, price, stock FROM components WHERE id = ?', (product_id,)).fetchone()
            if not db_item: return jsonify({'success': False, 'message': f'ไม่พบสินค้า ID {product_id}'}), 400

            current_stock = db_item['stock'] or 0
            if current_stock < qty:
                return jsonify({'success': False, 'message': f'สินค้า {db_item["name"]} เหลือไม่เพียงพอ'}), 400

            # ล้างตัวเลขราคาสินค้าเพื่อคำนวณบิลยอดสั่งซื้อ
            price_clean = ''.join(c for c in str(db_item['price']) if c.isdigit() or c == '.')
            item_price = int(float(price_clean)) if price_clean else 0
            total_bill_price += (item_price * qty)

            conn.execute('UPDATE components SET stock = stock - ? WHERE id = ?', (qty, product_id))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (db_item['name'], f'🛒 ลูกค้าสั่งเบิกตัดยอดคลังสินค้าจำนวน {qty} ชิ้น', now_str))

        # บันทึกข้อมูลบิลเบิกลงในฐานข้อมูลตาราง orders
        cursor = conn.execute('INSERT INTO orders (total_price, order_date, items_json) VALUES (?, ?, ?)',
                              (total_bill_price, now_str, json.dumps(cart_items)))
        order_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'สั่งซื้อเสร็จเรียบร้อย!', 'order_id': order_id})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ✨ เพิ่มหน้าโชว์รายละเอียดใบเบิกสินค้า (Order/Receipt View) ป้องกันเว็บขึ้น Error 404 หลังกดเบิกของ
@app.route('/order/<int:order_id>')
def order_detail(order_id):
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    if not order: return abort(404)

    import json
    order_dict = dict(order)
    order_dict['items'] = json.loads(order_dict['items_json'])
    return render_template('order.html', order=order_dict)


@app.route('/export_report')
def export_report():
    if not is_logged_in_admin(): return abort(403)

    conn = get_db()
    cursor = conn.execute('SELECT id, name, category, price, stock FROM components')
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID อุปกรณ์', 'ชื่ออะไหล่ชิ้นส่วน', 'หมวดหมู่', 'ราคาต่อชิ้น', 'คงเหลือในสต็อกจริง'])

    for row in rows:
        writer.writerow([row['id'], row['name'], row['category'], row['price'], row['stock']])

    csv_data = "\ufeff" + output.getvalue()
    now_date = datetime.now().strftime('%Y%m%d')
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=ElectroHub_StockReport_{now_date}.csv"}
    )


@app.route('/reset_db')
def reset_db():
    conn = get_db()
    conn.execute('DROP TABLE IF EXISTS components')
    conn.execute('DROP TABLE IF EXISTS stock_logs')
    conn.execute('DROP TABLE IF EXISTS orders')
    conn.execute('''
                 CREATE TABLE components
                 (
                     id            INTEGER PRIMARY KEY AUTOINCREMENT,
                     name          TEXT NOT NULL,
                     category      TEXT NOT NULL,
                     price         TEXT NOT NULL,
                     image_url     TEXT NOT NULL,
                     description   TEXT NOT NULL,
                     specs         TEXT NOT NULL,
                     stock         INTEGER DEFAULT 0,
                     datasheet_url TEXT
                 )
                 ''')
    conn.commit()
    conn.close()
    update_db_structure()
    return "รีเซ็ตคลังฐานข้อมูลเริ่มต้นสำเร็จแล้ว!"


if __name__ == '__main__':
    update_db_structure()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)