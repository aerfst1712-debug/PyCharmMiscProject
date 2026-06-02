from flask import Flask, render_template, request, redirect, url_for, abort, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash_messages'  # จำเป็นต้องใส่เพื่อใช้ระบบแจ้งเตือน (Flash)
DATABASE = 'electronics.db'

# 🔐 ตั้งรหัสผ่านลับของคุณที่นี่ (เปลี่ยนเป็นรหัสที่คุณต้องการได้เลย)
SECRET_PASSWORD = "mtc124"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# (โค้ดสร้าง Table คงไว้เหมือนเดิม)
def init_db():
    with get_db() as conn:
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
                         TEXT
                     )
                     ''')
        conn.commit()


init_db()


@app.route('/')
def home():
    conn = get_db()
    cursor = conn.execute('SELECT * FROM components')
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    cursor = conn.execute('SELECT * FROM components WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product is None:
        abort(404)

    product_dict = dict(product)
    product_dict['specs'] = [s.strip() for s in product_dict['specs'].split(',')] if product_dict['specs'] else []
    return render_template('product.html', product=product_dict)


# 🛠️ ปรับปรุงหน้าเพิ่มอุปกรณ์ให้ตรวจสอบรหัสผ่าน
@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']

        # 🔑 ตรวจสอบรหัสผ่านที่ผู้ใช้กรอกเข้ามา
        user_password = request.form['password']

        if user_password != SECRET_PASSWORD:
            # ถ้ารหัสไม่ถูกต้อง ให้ส่งข้อความเตือนและแจ้งความผิดพลาด
            flash('❌ รหัสผ่านไม่ถูกต้อง! คุณไม่มีสิทธิ์เพิ่มข้อมูลชิ้นส่วนนี้')
            return render_template('add.html', name=name, category=category, price=price, image_url=image_url,
                                   description=description, specs=specs)

        # ถ้ารหัสผ่านถูกต้อง บันทึกลงฐานข้อมูล SQLite ตามปกติ
        conn = get_db()
        conn.execute('''
                     INSERT INTO components (name, category, price, image_url, description, specs)
                     VALUES (?, ?, ?, ?, ?, ?)
                     ''', (name, category, price, image_url, description, specs))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('add.html')


if __name__ == '__main__':
    app.run()