<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ElectroHub Labs - คลังอุปกรณ์อิเล็กทรอนิกส์</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=Sarabun:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Sarabun', sans-serif; background-color: #f8fafc; color: #334155; }
        h1, h2, h3, .navbar-brand, .stat-num, .modal-title { font-family: 'Chakra Petch', sans-serif; }
        .navbar
{background - color: #ffffff !important; border-bottom: 2px solid #0ea5e9; }
        .stat - card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .stat-num { font-size: 2rem; font-weight: bold; color: #0ea5e9; }
        .card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; transition: transform 0.2s, box-shadow 0.2s; position: relative; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .price-tag
{color: #059669; font-weight: bold; font-size: 1.1rem; }
        .btn - view { background-color: #f1f5f9; color: #0284c7; border-radius: 20px; font-weight: bold; border: 1px solid #e2e8f0; }
        .btn-view:hover { background-color: #e2e8f0; }
        .btn-buy-now { background-color: #0ea5e9; color: #ffffff; border-radius: 20px; font-weight: bold; border: none; }
        .btn-buy-now:hover { background-color: #0284c7; }
        .admin-actions { position: absolute; top: 10px; right: 10px; z-index: 10; display: flex; gap: 5px; }
        .indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .bg-success-dot { background-color: #10b981; }
        .bg-warning-dot { background-color: #f59e0b; }
        .bg-danger-dot { background-color: #ef4444; }
        .log-box { background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; }

        /* 🛒 ตะกร้าสินค้า */
        .cart-badge { background-color: #ef4444; color: white; border-radius: 50%; padding: 2px 6px; font-size: 0.75rem; position: absolute; top: -5px; right: -5px; }
        .cart-sidebar { width: 380px !important; }
        .cart-item-img { width: 50px; height: 50px; object-fit: contain; background-color: #f8fafc; border-radius: 6px; }

/* 📋 สไตล์ป็อปอัพรายละเอียด */
        .spec-badge { background-color: #f1f5f9; border-left: 4px solid #0ea5e9; color: #1e293b; font-weight: 500; padding: 8px 12px; border-radius: 4px; font-size: 0.9rem; }
    </style>
</head>
<body>

    <nav class="navbar navbar-light p-3 shadow-sm sticky-top">
        <div class="container">
            <a class="navbar-brand fw-bold fs-3" href="/{% if is_admin %}?pw={{ pw }}&admin=true{% endif %}">⚡ ElectroHub <span style="color: #0ea5e9;">Labs</span></a>
            <div class="d-flex align-items-center gap-3">

                <button class="btn btn-outline-dark rounded-pill position-relative px-3 fw-bold btn-sm" type="button" data-bs-toggle="offcanvas" data-bs-target="#cartSidebar">
                    🛒 ตะกร้าของฉัน <span id="cartCountBadge" class="cart-badge d-none">0</span>
                </button>

                {% if show_login_box or is_admin %}
                <form method="GET" action="/" class="d-flex gap-1 align-items-center">
                    <input type="hidden" name="admin" value="true">
                    <input type="password" name="pw" class="form-control form-control-sm rounded-pill" style="width: 140px;" placeholder="รหัสผ่านแอดมิน" value="{{ pw if is_admin else '' }}">
                    <button type="submit" class="btn btn-dark btn-sm rounded-pill">🔒 ยืนยัน</button>
                </form>
                {% endif %}

                {% if is_admin %}
                    <a href="/add?pw={{ pw }}" class="btn btn-success btn-sm rounded-pill px-3 fw-bold">➕ เพิ่มเบอร์ IC</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="offcanvas offcanvas-end cart-sidebar" tabindex="-1" id="cartSidebar">
        <div class="offcanvas-header border-bottom">
            <h5 class="offcanvas-title fw-bold">🛒 ตะกร้าสินค้าของคุณ</h5>
            <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Close"></button>
        </div>
        <div class="offcanvas-body d-flex flex-column">
            <div class="d-flex justify-content-end mb-2">
                <button id="clearCartBtn" class="btn btn-link btn-sm text-secondary d-none p-0" onclick="clearCart()">🗑️ ล้างสินค้าทั้งหมด</button>
            </div>

            <div id="cartItemsList" class="flex-grow-1 overflow-auto">
                <p class="text-muted text-center my-5">ไม่มีสินค้าในตะกร้าขณะนี้</p>
            </div>
            <div class="border-top pt-3 mt-auto">
                <div class="d-flex justify-content-between mb-3">
                    <span class="fw-bold">ยอดเงินรวม:</span>
                    <span id="cartTotalPrice" class="fw-bold text-success fs-5">0 บาท</span>
                </div>
                <button id="checkoutBtn" class="btn btn-primary w-100 rounded-pill fw-bold py-2.5 d-none" onclick="processCheckout()">
                    💳 ยืนยันคำสั่งซื้อ (และตัดสต็อก)
                </button>
            </div>
        </div>
    </div>

    <div class="modal fade" id="productDetailModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content style-main-box p-3 border-0 shadow" style="border-radius: 16px;">
                <div class="modal-header border-0 pb-0">
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row g-4">
                        <div class="col-md-5 text-center">
                            <div class="p-3 border rounded bg-light mb-3">
                                <img id="modalImg" src="" alt="" class="img-fluid" style="max-height: 220px; object-fit: contain;">
                            </div>
                            <a id="modalDatasheet" href="" target="_blank" class="btn btn-sm btn-outline-info w-100 rounded-pill fw-bold mb-2">📄 เปิดคู่มือ Datasheet (PDF)</a>
                        </div>
                        <div class="col-md-7">
                            <span id="modalCategory" class="badge bg-primary mb-2"></span>
                            <h3 id="modalName" class="fw-bold text-dark"></h3>
                            <h5 id="modalPrice" class="text-success fw-bold my-2"></h5>
                            <div id="modalStockBadge" class="p-1 px-3 rounded small d-inline-block fw-bold mb-3"></div>

                            <h6 class="fw-bold text-primary mt-2">📌 รายละเอียด:</h6>
                            <p id="modalDescription" class="text-secondary small lh-lg"></p>

                            <h6 class="fw-bold text-primary mt-3">🛠️ สเปกทางเทคนิค:</h6>
                            <div id="modalSpecsList" class="d-flex flex-column gap-1"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container my-5">

        {% if is_admin %}
        <div class="row g-3 mb-5">
            <div class="col-md-3 col-6">
                <div class="stat-card">
                    <div class="text-muted small fw-bold">📦 เบอร์อะไหล่ทั้งหมด</div>
                    <div class="stat-num text-dark">{{ total_items }}</div>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="stat-card">
                    <div class="text-muted small fw-bold">🔢 จำนวนชิ้นรวมในคลัง</div>
                    <div class="stat-num text-primary">{{ total_stock }}</div>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="stat-card border-warning" style="background-color: #fffbdf;">
                    <div class="text-muted small fw-bold text-warning">⚠️ รายการที่ใกล้หมด (&lt;5)</div>
                    <div class="stat-num text-warning">{{ low_stock_count }}</div>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="stat-card border-danger" style="background-color: #fde8e8;">
                    <div class="text-muted small fw-bold text-danger">🚨 รายการที่หมดแล้ว</div>
                    <div class="stat-num text-danger">{{ out_of_stock_count }}</div>
                </div>
            </div>
        </div>
        {% endif %}

        <div class="text-center mb-5">
            <h1 class="fw-bold mb-2">📦 คลังข้อมูลส่วนประกอบอิเล็กทรอนิกส์</h1>
            <p class="text-muted">สืบค้นสเปก รายละเอียดชิ้นส่วน และข้อมูลทางเทคนิคได้อย่างรวดเร็ว</p>

            <form action="/" method="GET" class="d-flex gap-2 justify-content-center mt-4" style="max-width: 600px; margin: 0 auto;">
                {% if is_admin %}<input type="hidden" name="pw"
value= "{{ pw }}" > < input type= "hidden" name= "admin" value= "true" > { % endif %}
                <input type="text" name="search" class="form-control rounded-pill px-4 shadow-sm" placeholder="🔍 พิมพ์ชื่อเบอร์ IC หรือหมวดหมู่เพื่อค้นหา..." value="{{ search_query }}">
                <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold" style="background-color: #0ea5e9; border: none;">ค้นหา</button>
            </form>
        </div>

        <div class="d-flex flex-wrap gap-2 justify-content-center mb-5">
            <a href="/{% if is_admin %}?pw={{ pw }}&admin=true{% endif %}" class="btn rounded-pill px-3 fw-bold btn-sm {% if not current_category %}btn-primary{% else %}btn-outline-secondary{% endif %}" style="{% if not current_category %}background-color: #0ea5e9; border:none;{% endif %}">ทั้งหมด</a>
            {% for cat in categories %}
                <a href="/?category={{ cat }}{% if is_admin %}&pw={{ pw }}&admin=true{% endif %}" class="btn rounded-pill px-3 fw-bold btn-sm {% if current_category == cat %}btn-primary{% else %}btn-outline-secondary{% endif %}" style="{% if current_category == cat %}background-color: #0ea5e9; border:none;{% endif %}">{{ cat }}</a>
            {% endfor %}
        </div>

        <div class="row g-4 mb-5">
            {% if products %}
                {% for product in products %}
                <div class="col-md-4 col-sm-6">
                    <div class="card h-100 shadow-sm p-2">

                        {% if is_admin %}
                        <div class="admin-actions">
                            <a href="/edit/{{ product.id }}?pw={{ pw }}" class="btn btn-warning btn-sm rounded-circle shadow" title="แก้ไข">✏️</a>
                            <a href="/delete/{{ product.id }}?pw={{ pw }}" class="btn btn-danger btn-sm rounded-circle shadow" title="ลบ" onclick="return confirm('ต้องการลบชิ้นส่วนนี้?')">🗑️</a>
                        </div>
                        {% endif %}

                        <img src="{{ product.image_url }}" class="card-img-top rounded p-2" id="prod-img-{{ product.id }}" alt="{{ product.name }}" style="height: 180px; object-fit: contain; background: #f8fafc;">
                        <div class="card-body d-flex flex-column">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="badge bg-light text-primary border border-primary-subtle" id="prod-cat-{{ product.id }}">{{ product.category }}</span>
                                <span class="small fw-bold text-secondary">
                                    {% if (product.stock or 0) >= 15 %}
                                        <span class="indicator bg-success-dot"></span>คลัง: {{ product.stock or 0 }} ชิ้น
                                    {% elif (product.stock or 0) > 0 %}
                                        <span class="indicator bg-warning-dot"></span>ใกล้หมด: {{ product.stock or 0 }} ชิ้น
                                    {% else %}
                                        <span class="indicator bg-danger-dot"></span>ของหมด
                                    {% endif %}
                                </span>
                            </div>
                            <h4 class="card-title mb-2 text-dark" id="prod-name-{{ product.id }}">{{ product.name }}</h4>

                            <div class="d-none" id="prod-desc-{{ product.id }}">{{ product.description }}</div>
                            <div class="d-none" id="prod-specs-{{ product.id }}">{{ product.specs }}</div>
                            <div class="d-none" id="prod-ds-{{ product.id }}">{{ product.datasheet_url or '' }}</div>
                            <div class="d-none" id="prod-stocknum-{{ product.id }}">{{ product.stock or 0 }}</div>

                            <p class="card-text text-muted text-truncate mb-3">{{ product.description }}</p>

                            {% if is_admin %}
<div class="d-flex gap-1 align-items-center mb-3 justify-content-center border-top border-bottom py-2">
                                <span class="small text-muted me-2">ปรับคลัง:</span>
                                <a href="/update_stock/{{ product.id }}/decrease?pw={{ pw }}" class="btn btn-outline-danger btn-sm rounded-circle fw-bold {% if (product.stock or 0) <= 0 %}disabled{% endif %}" style="width: 28px; height: 28px; line-height: 12px;">-</a>
                                <span class="fw-bold mx-2">{{ product.stock or 0 }}</span>
                                <a href="/update_stock/{{ product.id }}/increase?pw={{ pw }}" class="btn btn-outline-success btn-sm rounded-circle fw-bold" style="width: 28px; height: 28px; line-height: 12px;">+</a>
                            </div>
                            {% endif %}

                            <div class="d-flex justify-content-between align-items-center mt-auto bg-transparent">
                                <span class="price-tag" id="prod-price-{{ product.id }}">ราคา: {{ product.price }}</span>
                            </div>
                            <div class="row g-2 mt-2 bg-transparent">
                                <div class="col-5 bg-transparent">
                                    <button class="btn btn-view btn-sm w-100 py-2" onclick="openDetailModal('{{ product.id }}')">รายละเอียด</button>
                                </div>
                                <div class="col-7 bg-transparent">
                                    {% if (product.stock or 0) > 0 %}
                                        <button class="btn btn-buy-now btn-sm w-100 py-2" onclick="addToCart('{{ product.id }}', '{{ product.stock }}')">🛒 ใส่ตะกร้า</button>
                                    {% else %}
                                        <button class="btn btn-secondary btn-sm w-100 py-2" disabled>❌ สินค้าหมด</button>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="text-center my-5 py-5 w-100">
                    <h3 class="text-muted">❌ ไม่พบส่วนประกอบอิเล็กทรอนิกส์ในกลุ่มนี้</h3>
                </div>
            {% endif %}
        </div>

        {% if is_admin %}
        <div class="log-box shadow-sm">
            <h5 class="fw-bold mb-3 text-secondary">📋 บันทึกประวัติการจัดการคลังล่าสุด (Admin Stock Logs)</h5>
            <div class="table-responsive">
                <table class="table table-hover table-sm m-0 small text-secondary">
                    <thead class="table-light">
                        <tr>
                            <th>เวลาจัดทำกิจกรรม</th>
                            <th>รายการเบอร์ IC</th>
                            <th>กิจกรรมการดำเนินงาน</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if logs %}
                            {% for log in logs %}
                            <tr>
                                <td><code>{{ log.timestamp }}</code></td>
                                <td class="fw-bold text-dark">{{ log.component_name }}</td>
                                <td>{{ log.action_type }}</td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="3" class="text-center py-2 text-muted">ยังไม่มีประวัติการปรับจำนวนสต็อกสินค้าในเวลานี้</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <script>
        let cart = JSON.parse(localStorage.getItem('electrohub_cart')) || [];
        updateCartUI();

        // 1. ฟังก์ชันเพิ่มสินค้าเข้าตะกร้า
        function addToCart(id, maxStock) {
            maxStock = parseInt(maxStock);
            let productInCart = cart.find(item => item.id === id);

            if (productInCart) {
                if (productInCart.qty >= maxStock) {
                    alert(`ขออภัย! ไม่สามารถสั่งเพิ่มได้ เนื่องจากคลังออนไลน์มีสินค้าชิ้นนี้อยู่สูงสุดเพียง ${maxStock} ชิ้นเท่านั้น`);
                    return;
                }
                productInCart.qty += 1;
            } else {
                let name = document.getElementById(`prod-name-${id}`).innerText;
                let img = document.getElementById(`prod-img-${id}`).src;
                let priceText = document.getElementById(`prod-price-${id}`).innerText;
                let priceNum = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;

                cart.push({
                    id: id,
                    name: name,
                    img: img,
                    price: priceNum,
                    maxStock: maxStock,
                    qty: 1
                });
            }
            saveCartAndRefresh();

            var offcanvasElement = document.getElementById('cartSidebar');
            var offcanvas = new bootstrap.Offcanvas(offcanvasElement);
            offcanvas.show();
        }

        // ✨ 2. ฟังก์ชันใหม่: สำหรับล้างตะกร้าสินค้าทั้งหมดในทีเดียว
        function clearCart() {
            if (confirm('คุณต้องการเคลียร์สินค้าทั้งหมดออกจากตะกร้าใช่หรือไม่?')) {
                cart = [];
                saveCartAndRefresh();
            }
        }

        function removeFromCart(id) {
            cart = cart.filter(item => item.id !== id);
            saveCartAndRefresh();
        }

        function changeQty(id, action) {
            let item = cart.find(i => i.id === id);
            if (item) {
                if (action === 'increase') {
                    if (item.qty >= item.maxStock) {
                        alert(`ไม่สามารถเพิ่มได้เกิน ${item.maxStock} ชิ้นตามสต็อกจริงได้`);
                        return;
                    }
                    item.qty += 1;
                } else if (action === 'decrease') {
                    item.qty -= 1;
                    if (item.qty <= 0) {
                        removeFromCart(id);
                        return;
                    }
                }
                saveCartAndRefresh();
            }
        }

        function saveCartAndRefresh() {
            localStorage.setItem('electrohub_cart', JSON.stringify(cart));
            updateCartUI();
        }

        function updateCartUI() {
            let listContainer = document.getElementById('cartItemsList');
            let badge = document.getElementById('cartCountBadge');
            let checkoutBtn = document.getElementById('checkoutBtn');
            let clearBtn = document.getElementById('clearCartBtn'); // ตัวปุ่มเคลียร์
            let totalLabel = document.getElementById('cartTotalPrice');

            let totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
            let totalPrice = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);

            if (totalQty > 0) {
                badge.innerText = totalQty;
                badge.classList.remove('d-none');
                checkoutBtn.classList.remove('d-none');
                clearBtn.classList.remove('d-none'); // แสดงปุ่มเคลียร์
            } else {
                badge.classList.add('d-none');
                checkoutBtn.classList.add('d-none');
                clearBtn.classList.add('d-none'); // ซ่อนปุ่มเคลียร์
            }

            totalLabel.innerText = totalPrice + ' บาท';

            if (cart.length === 0) {
                listContainer.innerHTML = '<p class="text-muted text-center my-5">ไม่มีสินค้าในตะกร้าขณะนี้</p>';
                return;
            }

            let html = '';
            cart.forEach(item => {
                html += `
                    <div class="d-flex align-items-center justify-content-between p-2 mb-3 border-bottom bg-transparent">
                        <img src="${item.img}" class="cart-item-img me-2">
                        <div class="flex-grow-1 bg-transparent">
                            <h6 class="mb-0 fw-bold text-dark small">${item.name}</h6>
                            <small class="text-muted">${item.price} บาท/ชิ้น</small>
                            <div class="d-flex align-items-center gap-1 mt-1 bg-transparent">
                                <button class="btn btn-outline-secondary btn-xs py-0 px-2 rounded" onclick="changeQty('${item.id}', 'decrease')">-</button>
                                <span class="px-2 small fw-bold">${item.qty}</span>
                                <button class="btn btn-outline-secondary btn-xs py-0 px-2 rounded" onclick="changeQty('${item.id}', 'increase')">+</button>
                            </div>
                        </div>
                        <div class="text-end bg-transparent">
                            <div class="fw-bold text-success small">${item.price * item.qty} บาท</div>
                            <button class="btn btn-link btn-sm text-danger p-0 mt-1" onclick="removeFromCart('${item.id}')">ลบ</button>
                        </div>
                    </div>
                `;
            });
            listContainer.innerHTML = html;
        }

        // ✨ 3. ฟังก์ชันใหม่: ดึงข้อมูลจากการ์ดมาประกอบร่างใส่ในกล่องป็อปอัพรายละเอียด (Modal)
        function openDetailModal(id) {
            let name = document.getElementById(`prod-name-${id}`).innerText;
            let img = document.getElementById(`prod-img-${id}`).src;
            let cat = document.getElementById(`prod-cat-${id}`).innerText;
            let price = document.getElementById(`prod-price-${id}`).innerText;
            let desc = document.getElementById(`prod-desc-${id}`).innerText;
            let specsRaw = document.getElementById(`prod-specs-${id}`).innerText;
            let dsUrl = document.getElementById(`prod-ds-${id}`).innerText;
            let stockNum = parseInt(document.getElementById(`prod-stocknum-${id}`).innerText) || 0;

            // ป้อนค่าเข้าป็อปอัพ
            document.getElementById('modalName').innerText = name;
            document.getElementById('modalImg').src = img;
            document.getElementById('modalCategory').innerText = cat;
            document.getElementById('modalPrice').innerText = price;
            document.getElementById('modalDescription').innerText = desc;

            // ปรับแต่ง Badge สถานะสต็อกในตัวป็อปอัพ
            let stockBadge = document.getElementById('modalStockBadge');
            if (stockNum >= 15) {
                stockBadge.className = "p-1 px-3 rounded small d-inline-block fw-bold mb-3 text-success bg-success-subtle";
                stockBadge.innerText = `📦 คลังพร้อมจ่าย: ${stockNum} ชิ้น`;
            } else if (stockNum > 0) {
                stockBadge.className = "p-1 px-3 rounded small d-inline-block fw-bold mb-3 text-warning bg-warning-subtle";
                stockBadge.innerText = `⚠️ อะไหล่ใกล้หมด: เหลือ ${stockNum} ชิ้น`;
            } else {
                stockBadge.className = "p-1 px-3 rounded small d-inline-block fw-bold mb-3 text-danger bg-danger-subtle";
                stockBadge.innerText = `❌ สินค้าหมดคลังชั่วคราว`;
            }

            // เปิด/ซ่อน ลิงก์คู่มือ Datasheet
            let dsBtn = document.getElementById('modalDatasheet');
            if (dsUrl && dsUrl.trim() !== '') {
                dsBtn.href = dsUrl;
                dsBtn.classList.remove('d-none');
            } else {
                dsBtn.classList.add('d-none');
            }

            // แยกและจัดทำรายการจุดเช็คสเปกข้อๆ
            let specsContainer = document.getElementById('modalSpecsList');
            specsContainer.innerHTML = '';
            if (specsRaw) {
                let specsArray = specsRaw.split(',');
                specsArray.forEach(spec => {
                    if (spec.trim() !== '') {
                        let div = document.createElement('div');
                        div.className = "spec-badge";
                        div.innerText = `✔️ ${spec.trim()}`;
                        specsContainer.appendChild(div);
                    }
                });
            }

            // สั่งเปิดป็อปอัพโชว์ขึ้นมาหน้าจอ
            let myModal = new bootstrap.Modal(document.getElementById('productDetailModal'));
            myModal.show();
        }

        // 4. ส่งตะกร้าไปเช็คเอาท์ตัดสต็อกที่เซิร์ฟเวอร์หลังบ้าน
        function processCheckout() {
            if (cart.length === 0) return;
            if (!confirm('ยืนยันรายการเพื่อสั่งซื้อและตัดสต็อกสินค้าออกจากระบบจำลองคลังออนไลน์?')) return;

            document.getElementById('checkoutBtn').disabled = true;
            document.getElementById('checkoutBtn').innerText = 'กำลังบันทึกสต็อกหลังบ้าน...';

            fetch('/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart: cart })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    cart = [];
                    saveCartAndRefresh();

                    var offcanvasElement = document.getElementById('cartSidebar');
                    var offcanvas = bootstrap.Offcanvas.getInstance(offcanvasElement);
                    if (offcanvas) offcanvas.hide();

                    location.reload();
                } else {
                    alert('คำสั่งซื้อล้มเหลว: ' + data.message);
                    document.getElementById('checkoutBtn').disabled = false;
                    document.getElementById('checkoutBtn').innerText = '💳 ยืนยันคำสั่งซื้อ (และตัดสต็อก)';
                }
            })
            .catch(err => {
                alert('เกิดข้อผิดพลาดในการเชื่อมต่อสต็อกคลาวด์: ' + err);
                document.getElementById('checkoutBtn').disabled = false;
                document.getElementById('checkoutBtn').innerText = '💳 ยืนยันคำสั่งซื้อ (และตัดสต็อก)';
            });
        }
    </script>
</body>
</html>