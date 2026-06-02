from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3

app = Flask(__name__)
DATABASE = 'electronics.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    # ตรวจสอบสิทธิ์แอดมินจากลิงก์ระบุ ?admin=true
    is_admin = request.args.get('admin') == 'true'

    conn = get_db()
    cursor = conn.execute('SELECT * FROM components')
    products = cursor.fetchall()
    conn.close()

    return render_template('index.html', products=products, is_admin=is_admin)


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

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        description = request.form['description']
        specs = request.form['specs']

        # บันทึกเข้าฐานข้อมูลทันทีโดยไม่ต้องเช็กส่วนรหัสผ่านแล้ว
        conn = get_db()
        conn.execute('''
                     INSERT INTO components (name, category, price, image_url, description, specs)
                     VALUES (?, ?, ?, ?, ?, ?)
                     ''', (name, category, price, image_url, description, specs))
        conn.commit()
        conn.close()

        # เพิ่มเสร็จ ให้เด้งกลับหน้าหลักพร้อมคงสิทธิ์แอดมินไว้ (ปุ่มจะได้ไม่หาย)
        return redirect(url_for('home', admin='true'))

    return render_template('add.html', is_admin=is_admin)


if __name__ == '__main__':
    app.run(debug=True)