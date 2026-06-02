from flask import Flask, render_template, request, redirect, url_for, abort, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash_messages'
DATABASE = 'electronics.db'

SECRET_PASSWORD = "mtc123"  # รหัสผ่านสำหรับการบันทึกเข้าฐานข้อมูล


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# (ฟังก์ชัน init_db คงไว้ตามเดิม)

@app.route('/')
def home():
    # ตรวจสอบว่าเช็กสิทธิ์แอดมินจากลิงก์ระบุ ?admin=true หรือไม่
    is_admin = request.args.get('admin') == 'true'

    conn = get_db()
    cursor = conn.execute('SELECT * FROM components')
    products = cursor.fetchall()
    conn.close()

    # ส่งค่า is_admin ไปที่หน้า index.html
    return render_template('index.html', products=products, is_admin=is_admin)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # ดักรับค่า admin จากหน้ารายละเอียดด้วย เพื่อให้เวลากดกลับ สิทธิ์จะได้ไม่หลุด
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

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']
        user_password = request.form['password']

        if user_password != SECRET_PASSWORD:
            flash('❌ รหัสผ่านไม่ถูกต้อง! คุณไม่มีสิทธิ์เพิ่มข้อมูลชิ้นส่วนนี้')
            return render_template('add.html', name=name, category=category, price=price, image_url=image_url,
                                   description=description, specs=specs, is_admin=is_admin)

        conn = get_db()
        conn.execute('''
                     INSERT INTO components (name, category, price, image_url, description, specs)
                     VALUES (?, ?, ?, ?, ?, ?)
                     ''', (name, category, price, image_url, description, specs))
        conn.commit()
        conn.close()

        # เพิ่มเสร็จให้เด้งกลับหน้าหลักพร้อมสิทธิ์แอดมิน
        return redirect(url_for('home', admin='true'))

    return render_template('add.html', is_admin=is_admin)


if __name__ == '__main__':
    app.run(debug=True)