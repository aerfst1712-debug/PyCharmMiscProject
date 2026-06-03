from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, Response
import sqlite3
import csv
import io
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'electrohub_labs_ultra_secret_key_2026'

DATABASE = 'electronics.db'
ADMIN_PASSWORD = '1234'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def update_db_structure():
    conn = get_db()
    # 1. ตารางสินค้าหลัก
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS components
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
                     TEXT,
                     price
                     INTEGER
                     DEFAULT
                     0,
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
                 )
                 ''')

    # 2. ตาราง Log กิจกรรมด่วน
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

    # 3. ตารางประวัติการเบิก/สั่งซื้อ (Master Orders)
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS orders
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     order_date
                     TEXT
                     NOT
                     NULL,
                     total_price
                     INTEGER
                     NOT
                     NULL
                 )
                 ''')

    # 4. ตารางรายละเอียดสินค้าในใบเบิก (Order Items)
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS order_items
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     order_id
                     INTEGER
                     NOT
                     NULL,
                     component_name
                     TEXT
                     NOT
                     NULL,
                     price_per_piece
                     INTEGER
                     NOT
                     NULL,
                     quantity
                     INTEGER
                     NOT
                     NULL,
                     FOREIGN
                     KEY
                 (
                     order_id
                 ) REFERENCES orders
                 (
                     id
                 )
                     )
                 ''')
    conn.commit()

    # ตรวจสอบการเติมข้อมูลตัวอย่างพื้นฐาน
    cursor = conn.execute('SELECT COUNT(*) FROM components')
    if cursor.fetchone()[0] == 0:
        default_components = [
            ('IC LM358', 'Integrated Circuit', 50, 'https://th.rs-online.com/images/F4852924-01.jpg',
             'ไอซีขยายสัญญาณ Low Power Dual Operational Amplifier นิยมใช้ในวงจรกรองสัญญาณและวงจรเปรียบเทียบแรงดัน',
             'ขาใช้งาน: 8 พิน\nแรงดันไฟเลี้ยง: 3V ถึง 32V\nจำนวนช่องสัญญาณ: 2 ช่อง', 100,
             'https://www.ti.com/lit/ds/symlink/lm358.pdf'),
            ('Arduino Uno R3', 'Microcontroller', 250,
             'https://docs.arduino.cc/static/29849b29d499ec249f056bc293d07ec5/A000066_featured.jpg',
             'บอร์ดไมโครคอนโทรลเลอร์โอเพนซอร์สยอดนิยมสำหรับเรียนรู้และพัฒนาระบบฝังตัว วงจรอิเล็กทรอนิกส์ และหุ่นยนต์',
             'ชิปหลัก: ATmega328P\nแรงดันใช้งาน: 5V\nขา Digital I/O: 14 ขา', 4,
             'https://docs.arduino.cc/resources/datasheets/A000066-datasheet-pdf')
        ]
        conn.executemany('''
                         INSERT INTO components (name, category, price, image_url, description, specs, stock,
                                                 datasheet_url)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         ''', default_components)
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

    # คำนวณสรุปแดชบอร์ด + ระบบเพิ่มฟีเจอร์คำนวณมูลค่ารวมสินค้าทั้งหมดในคลัง
    total_items = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0]
    total_stock_res = conn.execute('SELECT SUM(stock) FROM components').fetchone()[0]
    total_stock = total_stock_res if total_stock_res is not None else 0
    low_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock < 5 AND stock > 0').fetchone()[0]
    out_of_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock == 0').fetchone()[0]

    # 🌟 ฟีเจอร์เพิ่มเติม: สรุปมูลค่าเงินทุนจมในคลังสินค้าทั้งหมด
    total_value_res = conn.execute('SELECT SUM(price * stock) FROM components').fetchone()[0]
    total_warehouse_value = total_value_res if total_value_res is not None else 0

    # ดึงประวัติ Logs ล่าสุด 5 แถว
    try:
        log_cursor = conn.execute('SELECT * FROM stock_logs ORDER BY id DESC LIMIT 5')
        logs = log_cursor.fetchall()
    except sqlite3.OperationalError:
        logs = []

    # ดึงประวัติใบเบิก/ประวัติสั่งซื้อล่าสุด 5 บิล
    order_cursor = conn.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 5')
    recent_orders = order_cursor.fetchall()

    conn.close()
    return render_template('index.html',
                           products=products,
                           is_admin=is_admin,
                           search_query=search_query,
                           categories=categories,
                           current_category=category_filter,
                           total_items=total_items,
                           total_stock=total_stock,
                           low_stock_count=low_stock_count,
                           out_of_stock_count=out_of_stock_count,
                           total_warehouse_value=total_warehouse_value,
                           logs=logs,
                           recent_orders=recent_orders)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,)).fetchone()
    conn.close()

    if not row:
        return abort(404)

    product = dict(row)
    if product['specs']:
        product['specs'] = product['specs'].splitlines()
    else:
        product['specs'] = []

    return render_template('detail.html', product=product, is_admin=is_logged_in_admin())


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


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if not is_logged_in_admin(): return abort(403)

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        try:
            price = int(request.form['price'])
        except ValueError:
            price = 0

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
        try:
            price = int(request.form['price'])
        except ValueError:
            price = 0

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


# 🌟 ฟีเจอร์: บันทึกข้อมูลใบเสร็จตัดยอดคลังสินค้าลง Database ตัวจริงเรียบร้อย
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart_items = data.get('cart', [])
    if not cart_items: return jsonify({'success': False, 'message': 'ไม่มีสินค้าในตะกร้า'}), 400

    conn = get_db()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    try:
        # 1. คำนวณยอดเงินรวมเพื่อเปิดบิล Master Order
        total_price = 0
        for item in cart_items:
            total_price += int(item.get('price', 0)) * int(item.get('qty', 1))

        cursor = conn.execute('INSERT INTO orders (order_date, total_price) VALUES (?, ?)', (now_str, total_price))
        order_id = cursor.lastrowid

        # 2. ทำการเช็คตัดสต็อกพัสดุทีละรายการ พร้อมบันทึกรายละเอียดประวัติบิลย่อย
        for item in cart_items:
            product_id = item.get('id')
            qty = int(item.get('qty', 1))

            db_item = conn.execute('SELECT name, stock, price FROM components WHERE id = ?', (product_id,)).fetchone()
            if not db_item: return jsonify({'success': False, 'message': f'ไม่พบสินค้าไอดี {product_id}'}), 400

            current_stock = db_item['stock'] or 0
            if current_stock < qty:
                return jsonify(
                    {'success': False, 'message': f'สินค้า {db_item["name"]} เหลือสต็อกไม่เพียงพอกับการเบิก'}), 400

            # บันทึกตัดยอดและสร้างประวัติความเชื่อมโยงในระบบฐานข้อมูล
            conn.execute('UPDATE components SET stock = stock - ? WHERE id = ?', (qty, product_id))
            conn.execute(
                'INSERT INTO order_items (order_id, component_name, price_per_piece, quantity) VALUES (?, ?, ?, ?)',
                (order_id, db_item['name'], db_item['price'], qty))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (db_item['name'], f'🛒 เบิกตัดยอดคลังออกจากระบบ {qty} ชิ้น (บิลใบเบิกเลขที่ #{order_id})',
                          now_str))

        conn.commit()
        conn.close()
        return jsonify(
            {'success': True, 'message': f'สร้างใบเบิกจ่ายพัสดุและตัดคลังสินค้าเลขที่ #{order_id} สำเร็จแล้ว!'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# 🌟 ฟีเจอร์: เปิดดูรายละเอียดใบเบิกสินค้า (Order Invoice Preview) ย้อนหลัง
@app.route('/order/<int:order_id>')
def view_order(order_id):
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order:
        conn.close()
        return abort(404)

    items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
    conn.close()
    return render_template('order.html', order=order, items=items)


# 🌟 ฟีเจอร์: ส่งออกข้อมูล (Backup) ออกมาเป็นไฟล์ข้อมูล CSV สำหรับอัปโหลดกลับเข้าฐานข้อมูลได้
@app.route('/export_report')
def export_report():
    if not is_logged_in_admin(): return abort(403)

    conn = get_db()
    cursor = conn.execute(
        'SELECT id, name, category, price, image_url, description, specs, stock, datasheet_url FROM components')
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'category', 'price', 'image_url', 'description', 'specs', 'stock', 'datasheet_url'])

    for row in rows:
        writer.writerow(
            [row['id'], row['name'], row['category'], row['price'], row['image_url'], row['description'], row['specs'],
             row['stock'], row['datasheet_url']])

    csv_data = "\ufeff" + output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=ElectroHub_MasterBackup.csv"}
    )


# 🌟 ฟีเจอร์: อัปโหลดไฟล์ CSV (Restore Backup) ย้อนกลับมาเพื่อเติมเต็มฐานข้อมูลในระบบป้องกัน Render รีเซ็ตไฟล์
@app.route('/import_report', methods=['POST'])
def import_report():
    if not is_logged_in_admin(): return abort(403)

    file = request.files.get('backup_file')
    if not file: return redirect(url_for('home'))

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    header = next(csv_input)  # ข้ามหัวตาราง

    conn = get_db()
    # ล้างข้อมูลเดิมออกชั่วคราวเพื่อเขียนบันทึกไฟล์ข้อมูลสำรองทับให้เรียบร้อย
    conn.execute('DELETE FROM components')

    for row in csv_input:
        if not row: continue
        conn.execute('''
                     INSERT INTO components (id, name, category, price, image_url, description, specs, stock,
                                             datasheet_url)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                     ''', (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]))

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                 ('ระบบหลักคลังข้อมูล', '🔄 นำเข้าไฟล์สำรองเพื่อกู้คืนระบบผ่านชุดรายงาน CSV สำเร็จ', now_str))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    update_db_structure()
    app.run(debug=True)