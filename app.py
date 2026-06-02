from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'electronics.db'
ADMIN_PASSWORD = '1234'  # 🔑 รหัสผ่านแอดมิน


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
             'https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf')
        ]
        conn.executemany('''
                         INSERT INTO components (name, category, price, image_url, description, specs, stock,
                                                 datasheet_url)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         ''', default_components)
        conn.commit()

    conn.close()


@app.route('/')
def home():
    # 📌 เช็กว่ามีการพิมพ์ต่อท้ายด้วย ?admin=true หรือไม่
    show_login_box = (request.args.get('admin', '').lower() == 'true')

    password_input = request.args.get('pw', '')
    is_admin = (password_input == ADMIN_PASSWORD)

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

    total_items = 0
    total_stock = 0
    low_stock_count = 0
    out_of_stock_count = 0
    logs = []

    if is_admin:
        total_items = conn.execute('SELECT COUNT(*) FROM components').fetchone()[0]
        total_stock_res = conn.execute('SELECT SUM(stock) FROM components').fetchone()[0]
        total_stock = total_stock_res if total_stock_res is not None else 0
        low_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock < 5 AND stock > 0').fetchone()[0]
        out_of_stock_count = conn.execute('SELECT COUNT(*) FROM components WHERE stock == 0').fetchone()[0]

        try:
            log_cursor = conn.execute('SELECT * FROM stock_logs ORDER BY id DESC LIMIT 5')
            logs = log_cursor.fetchall()
        except sqlite3.OperationalError:
            logs = []

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
                           pw=password_input,
                           logs=logs,
                           show_login_box=show_login_box)  # ส่งสถานะการซ่อน/แสดงกล่องล็อกอินไปที่ HTML


@app.route('/update_stock/<int:product_id>/<string:action>')
def update_stock(product_id, action):
    password_input = request.args.get('pw', '')
    if password_input != ADMIN_PASSWORD:
        return abort(403)

    conn = get_db()
    comp = conn.execute('SELECT name, stock FROM components WHERE id = ?', (product_id,)).fetchone()

    if comp:
        current_stock = comp['stock'] or 0
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        if action == 'increase':
            conn.execute('UPDATE components SET stock = stock + 1 WHERE id = ?', (product_id,))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (comp['name'], '➕ เพิ่มสต็อกเป็น ' + str(current_stock + 1) + ' ชิ้น', now_str))
        elif action == 'decrease' and current_stock > 0:
            conn.execute('UPDATE components SET stock = MAX(0, stock - 1) WHERE id = ?', (product_id,))
            conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                         (comp['name'], '➖ ลดสต็อกเหลือ ' + str(current_stock - 1) + ' ชิ้น', now_str))

        conn.commit()
    conn.close()
    return redirect(url_for('home', pw=password_input, admin='true' if password_input == ADMIN_PASSWORD else 'false'))


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    password_input = request.args.get('pw', '')
    is_admin = (password_input == ADMIN_PASSWORD)

    conn = get_db()
    cursor = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product is None:
        abort(404)

    product_dict = dict(product)
    product_dict['specs'] = [s.strip() for s in product_dict['specs'].split(',')] if product_dict['specs'] else []
    return render_template('product.html', product=product_dict, is_admin=is_admin, pw=password_input)


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    password_input = request.args.get('pw', '')
    if password_input != ADMIN_PASSWORD:
        return abort(403)

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']
        stock = request.form.get('stock', 0, type=int)
        datasheet_url = request.form.get('datasheet_url', '')

        conn = get_db()
        conn.execute('''
                     INSERT INTO components (name, category, price, image_url, description, specs, stock, datasheet_url)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                     ''', (name, category, price, image_url, description, specs, stock, datasheet_url))

        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (name, '🆕 เพิ่มอุปกรณ์ใหม่เข้าคลังข้อมูล', now_str))

        conn.commit()
        conn.close()
        return redirect(url_for('home', pw=password_input, admin='true'))

    return render_template('add.html', is_admin=True, pw=password_input)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    password_input = request.args.get('pw', '')
    if password_input != ADMIN_PASSWORD:
        return abort(403)

    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']
        stock = request.form.get('stock', 0, type=int)
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
                     (name, '✏️ แก้ไขอัปเดตรายละเอียดข้อมูลข้อมูล', now_str))

        conn.commit()
        conn.close()
        return redirect(url_for('product_detail', product_id=product_id, pw=password_input))

    cursor = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return render_template('edit.html', product=product, is_admin=True, pw=password_input)


@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    password_input = request.args.get('pw', '')
    if password_input != ADMIN_PASSWORD:
        return abort(403)

    conn = get_db()
    comp = conn.execute('SELECT name FROM components WHERE id = ?', (product_id,)).fetchone()
    if comp:
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        conn.execute('INSERT INTO stock_logs (component_name, action_type, timestamp) VALUES (?, ?, ?)',
                     (comp['name'], '🗑️ ลบอุปกรณ์นี้ออกจากคลังระบบ', now_str))
        conn.execute('DELETE FROM components WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home', pw=password_input, admin='true'))


@app.route('/reset_db')
def reset_db():
    conn = get_db()
    conn.execute('DROP TABLE IF EXISTS components')
    conn.execute('DROP TABLE IF EXISTS stock_logs')
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
    return "รีเซ็ตตารางสำเร็จแล้ว!"


if __name__ == '__main__':
    update_db_structure()
    app.run(debug=True)