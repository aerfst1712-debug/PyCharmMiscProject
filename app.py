from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3

app = Flask(__name__)
DATABASE = 'electronics.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def update_db_structure():
    conn = get_db()
    # 1. ตรวจสอบและเพิ่มคอลัมน์สต็อกและ Datasheet (ถ้ายังไม่มี)
    try:
        conn.execute("ALTER TABLE components ADD COLUMN stock INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE components ADD COLUMN datasheet_url TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()

    # 2. ⚡ ส่วนล็อกข้อมูลเริ่มต้น: ระบบจะตรวจสอบว่าคลังว่างเปล่าไหม ถ้าว่างจะใส่ข้อมูลนี้ให้ทันที
    cursor = conn.execute('SELECT COUNT(*) FROM components')
    if cursor.fetchone()[0] == 0:
        # คุณสามารถเปลี่ยนชื่อ รูปภาพ หรือราคาของอุปกรณ์เริ่มต้นตรงนี้ได้ตามต้องการเลยครับ
        default_components = [
            (
                'IC LM358',
                'Integrated Circuit',
                '50 บาท',
                'https://th.rs-online.com/images/F4852924-01.jpg',
                'ไอซีขยายสัญญาณ Low Power Dual Operational Amplifier นิยมใช้ในวงจรกรองสัญญาณและวงจรเปรียบเทียบแรงดัน',
                'ขาใช้งาน: 8 พิน, แรงดันไฟเลี้ยง: 3V ถึง 32V, จำนวนช่องสัญญาณ: 2 ช่อง',
                100,
                'https://www.ti.com/lit/ds/symlink/lm358.pdf'
            ),
            (
                'Arduino Uno R3',
                'Microcontroller',
                '250 บาท',
                'https://docs.arduino.cc/static/29849b29d499ec249f056bc293d07ec5/A000066_featured.jpg',
                'บอร์ดไมโครคอนโทรลเลอร์โอเพนซอร์สยอดนิยมสำหรับเรียนรู้และพัฒนาระบบฝังตัว วงจรอิเล็กทรอนิกส์ และหุ่นยนต์',
                'ชิปหลัก: ATmega328P, แรงดันใช้งาน: 5V, ขา Digital I/O: 14 ขา, ขา Analog Input: 6 ขา',
                50,
                'https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf'
            )
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
    is_admin = request.args.get('admin') == 'true'
    search_query = request.args.get('search', '').strip()

    conn = get_db()
    if search_query:
        query = "SELECT * FROM components WHERE name LIKE ? OR category LIKE ?"
        cursor = conn.execute(query, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor = conn.execute('SELECT * FROM components')

    products = cursor.fetchall()
    conn.close()

    return render_template('index.html', products=products, is_admin=is_admin, search_query=search_query)


@app.route('/reset_db')
def reset_db():
    conn = get_db()
    conn.execute('DROP TABLE IF EXISTS components')
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

    # สั่งให้ใส่ข้อมูลเริ่มต้นเข้าไปใหม่ทันทีหลังจากล้างตาราง
    update_db_structure()
    return "ล้างฐานข้อมูลเก่าและอัปเกรดระบบคลังพร้อมตัวอย่างอะไหล่เริ่มต้นเรียบร้อยแล้ว! กดกลับหน้าหลักได้เลย"


@app.route('/update_stock/<int:product_id>/<string:action>')
def update_stock(product_id, action):
    is_admin = request.args.get('admin') == 'true'
    conn = get_db()

    if action == 'increase':
        conn.execute('UPDATE components SET stock = stock + 1 WHERE id = ?', (product_id,))
    elif action == 'decrease':
        conn.execute('UPDATE components SET stock = MAX(0, stock - 1) WHERE id = ?', (product_id,))

    conn.commit()
    conn.close()
    return redirect(url_for('home', admin='true' if is_admin else 'false'))


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    is_admin = request.args.get('admin') == 'true'

    conn = get_db()
    cursor = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product is None:
        abort(404)

    product_dict = dict(product)
    product_dict['specs'] = [s.strip() for s in product_dict['specs'].split(',')] if product_dict['specs'] else []
    return render_template('product.html', product=product_dict, is_admin=is_admin)


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    is_admin = request.args.get('admin') == 'true'
    if not is_admin:
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
        conn.commit()
        conn.close()

        return redirect(url_for('home', admin='true'))

    return render_template('add.html', is_admin=is_admin)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    is_admin = request.args.get('admin') == 'true'
    if not is_admin:
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
        conn.commit()
        conn.close()
        return redirect(url_for('product_detail', product_id=product_id, admin='true'))

    cursor = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return render_template('edit.html', product=product, is_admin=is_admin)


@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    is_admin = request.args.get('admin') == 'true'
    if not is_admin:
        return abort(403)

    conn = get_db()
    conn.execute('DELETE FROM components WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home', admin='true'))


if __name__ == '__main__':
    update_db_structure()
    app.run(debug=True)