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
    try:
        conn.execute("ALTER TABLE components ADD COLUMN stock INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE components ADD COLUMN datasheet_url TEXT")
    except sqlite3.OperationalError:
        pass
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


# 📝 1. ระบบแก้ไขข้อมูลอะไหล่ (เฉพาะแอดมิน)
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


# ❌ 2. ระบบลบอะไหล่ออกจากคลังข้อมูล (เฉพาะแอดมิน)
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