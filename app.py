from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import hashlib
import random
import database
import qrcode
import os
import hmac
import time

app = Flask(__name__)
app.secret_key = "smart_scan_secret_key"

database.init_db()

products = {
    "PROD001": {"name": "Notebook", "price": 40, "category": "Stationery", "image": "notebook.png"},
    "PROD002": {"name": "Pen", "price": 10, "category": "Stationery", "image": "pen.png"},
    "PROD003": {"name": "Pencil", "price": 5, "category": "Stationery", "image": "pencil.png"},
    "PROD004": {"name": "Water Bottle", "price": 150, "category": "Beverages", "image": "waterbottle.png"},
    "PROD005": {"name": "Cold Drink", "price": 45, "category": "Beverages", "image": "sodacan.png"},
    "PROD006": {"name": "Juice", "price": 35, "category": "Beverages", "image": "juice.png"},
    "PROD007": {"name": "Chips", "price": 20, "category": "Snacks", "image": "chipspacket.png"},
    "PROD008": {"name": "Chocolate", "price": 30, "category": "Snacks", "image": "chocolate.png"},
    "PROD009": {"name": "Biscuits", "price": 25, "category": "Groceries", "image": "biscuits.png"},
    "PROD010": {"name": "Soap", "price": 35, "category": "Groceries", "image": "soap.png"}
}

SECRET_KEY = "smart_scan_secret_2026"

# Password needed to open the Admin dashboard.
# CHANGE THIS before your demo. (On Render you can instead set an environment variable named ADMIN_PASSWORD.)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin@123")
ADMIN_TIMEOUT = 300  # admin dashboard locks itself after 5 minutes

if not os.path.exists("static/product_qr"):
    os.makedirs("static/product_qr")

for code in products:
    qr_path = f"static/product_qr/{code}.png"
    if not os.path.exists(qr_path):
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(code)
        qr.make()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)


def group_by_category():
    categories = {}
    for code, info in products.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((code, info))
    return categories

# ---------------- Login check (runs before every page) ----------------

@app.before_request
def require_login():
    # Anyone can look around the store; shopping steps need a login
    open_pages = ["home", "show_products", "login", "signup", "logout", "static", "saved_receipt"]
    if request.endpoint in open_pages:
        return None
    if not session.get("user_id"):
        if request.method == "POST":
            return jsonify({"success": False, "valid": False, "message": "Please log in first."}), 401
        return redirect(url_for("login"))

# ---------------- Pages ----------------

@app.route("/")
def home():
    return render_template("home.html", products=products, categories=group_by_category())

@app.route("/products")
def show_products():
    return render_template("products.html", categories=group_by_category())

# ---------------- Login / Signup / Logout ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            return render_template("signup.html", error="Please fill all fields. Password must be at least 6 characters.")

        password_hash = generate_password_hash(password)
        created = database.add_user(name, email, password_hash)

        if not created:
            return render_template("signup.html", error="This email is already registered. Please log in.")

        user = database.get_user_by_email(email)
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("home"))

    return render_template("signup.html", error=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = database.get_user_by_email(email)

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        return render_template("login.html", error="Wrong email or password.")

    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- Shopping ----------------

@app.route("/scan")
def scan_page():
    return render_template("scan.html")

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data = request.get_json()
    code = data.get("code")

    if code not in products:
        return jsonify({"success": False, "message": "Unknown product code"})

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(code)
    session.modified = True

    return jsonify({"success": True, "message": f"Added {products[code]['name']} to cart"})

@app.route("/cart")
def view_cart():
    cart_codes = session.get("cart", [])
    cart_items = []
    total = 0

    for code in cart_codes:
        product = products[code]
        cart_items.append(product)
        total += product["price"]

    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/remove_from_cart/<int:index>")
def remove_from_cart(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session["cart"] = cart
        session.modified = True
    return redirect(url_for("view_cart"))

@app.route("/payment")
def payment_page():
    cart_codes = session.get("cart", [])
    total = sum(products[code]["price"] for code in cart_codes)
    return render_template("payment.html", total=total, item_count=len(cart_codes))

@app.route("/process_payment", methods=["POST"])
def process_payment():
    data = request.get_json(silent=True) or {}
    customer_name = session.get("user_name") or data.get("name", "Customer")

    cart_codes = session.get("cart", [])
    total = sum(products[code]["price"] for code in cart_codes)

    order_id = str(uuid.uuid4())[:8]
    signature = hashlib.sha256(f"{order_id}{SECRET_KEY}".encode()).hexdigest()[:12]

    database.save_order(order_id, cart_codes, total, "PAID", signature, False)

    session["cart"] = []
    session["last_order"] = order_id
    session["customer_name"] = customer_name

    return jsonify({"success": True, "order_id": order_id})

def format_code(order_id):
    """A1B2C3D4 -> A1B2-C3D4 (easy to read out loud)"""
    o = order_id.upper()
    return o[:4] + "-" + o[4:]

def build_bill(order):
    item_counts = {}
    for code in order["items"]:
        if code in products:
            name = products[code]["name"]
            if name not in item_counts:
                item_counts[name] = {"qty": 0, "price": products[code]["price"], "image": products[code]["image"]}
            item_counts[name]["qty"] += 1
    return [{"name": n, "qty": d["qty"], "price": d["price"], "image": d["image"],
             "subtotal": d["qty"] * d["price"]} for n, d in item_counts.items()]

def make_receipt_qr(order_id, signature):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(f"{order_id}|{signature}")
    qr.make()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"static/product_qr/receipt_{order_id}.png")
    return f"receipt_{order_id}.png"

@app.route("/receipt")
def receipt_page():
    order_id = session.get("last_order")
    order = database.get_order(order_id) if order_id else None

    if not order:
        return render_template("receipt.html", order_id=None, total=0, qr_filename=None,
                               bill_items=[], customer_name=session.get("user_name", "Customer"))

    qr_filename = make_receipt_qr(order_id, order["signature"])
    share_url = url_for("saved_receipt", order_id=order_id, signature=order["signature"], _external=True)
    return render_template("receipt.html", order_id=order_id, total=order["total"],
                           qr_filename=qr_filename, bill_items=build_bill(order),
                           customer_name=session.get("customer_name", "Customer"),
                           exit_code=format_code(order_id), share_url=share_url, public=False)

# Anyone with the link can open the receipt again (the link contains the secret signature)
@app.route("/r/<order_id>/<signature>")
def saved_receipt(order_id, signature):
    order = database.get_order(order_id)
    if not order or order["signature"] != signature:
        return render_template("receipt.html", order_id=None, total=0, qr_filename=None,
                               bill_items=[], customer_name="Customer", public=True), 404
    qr_filename = make_receipt_qr(order_id, signature)
    share_url = url_for("saved_receipt", order_id=order_id, signature=signature, _external=True)
    return render_template("receipt.html", order_id=order_id, total=order["total"],
                           qr_filename=qr_filename, bill_items=build_bill(order),
                           customer_name="Customer", exit_code=format_code(order_id),
                           share_url=share_url, public=True)

# ---------------- Exit verification and admin ----------------

@app.route("/verify")
def verify_page():
    return render_template("verify.html")

def verify_order(order, order_id, manual=False):
    """Shared checks for scanned QR and manual code entry."""
    if order["used"]:
        return {"valid": False, "message": "❌ This QR was already used!"}
    if order["status"] != "PAID":
        return {"valid": False, "message": "❌ Order not paid"}

    database.mark_order_used(order_id)

    item_counts = {}
    for code in order["items"]:
        if code in products:
            name = products[code]["name"]
            item_counts[name] = item_counts.get(name, 0) + 1
    item_list = [f"{name} x{qty}" for name, qty in item_counts.items()]

    # manual entry is always inspected: staff has no QR proof
    if manual or random.random() < 0.2:
        msg = "⚠️ Manual entry — please check the bag against the list." if manual else "⚠️ FLAGGED for random check — please show bag contents to staff."
        return {"valid": True, "flagged": True, "order_id": order_id, "total": order["total"], "items": item_list, "message": msg}
    return {"valid": True, "flagged": False, "order_id": order_id, "total": order["total"], "items": item_list, "message": "✅ Verified — Allow Exit"}

@app.route("/check_order", methods=["POST"])
def check_order():
    data = request.get_json(silent=True) or {}
    scanned_text = data.get("code") or ""

    try:
        order_id, signature = scanned_text.split("|")
    except ValueError:
        return jsonify({"valid": False, "message": "Invalid QR format"})

    order = database.get_order(order_id)
    if not order:
        return jsonify({"valid": False, "message": "❌ Order not found"})
    if order["signature"] != signature:
        return jsonify({"valid": False, "message": "❌ Invalid / tampered QR code"})
    return jsonify(verify_order(order, order_id))

# Staff only: the customer's QR can't be scanned, so staff types the exit code printed under the QR
@app.route("/manual_verify", methods=["POST"])
def manual_verify():
    data = request.get_json(silent=True) or {}

    # The admin password is needed for EVERY manual entry (never remembered)
    password = data.get("password") or ""
    if not password:
        return jsonify({"valid": False, "message": "🔒 Enter the admin password to use manual entry."}), 403
    if not hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        time.sleep(1)  # slows down password guessing
        return jsonify({"valid": False, "message": "❌ Wrong admin password."}), 403

    code = "".join(ch for ch in (data.get("code") or "") if ch.isalnum()).lower()
    order = database.get_order(code) if code else None

    # Auto-lock: after any manual entry the admin dashboard is locked again too
    session.pop("is_admin", None)
    session.pop("admin_at", None)

    if not order:
        return jsonify({"valid": False, "message": "❌ No order with that exit code"})
    return jsonify(verify_order(order, code, manual=True))

def admin_active():
    """True only while the admin is unlocked AND has been active in the last 5 minutes."""
    if not session.get("is_admin"):
        return False
    if time.time() - session.get("admin_at", 0) > ADMIN_TIMEOUT:
        session.pop("is_admin", None)
        session.pop("admin_at", None)
        return False
    session["admin_at"] = time.time()
    return True

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    go_verify = request.args.get("next") == "verify"
    target = "verify_page" if go_verify else "admin_page"

    if admin_active():
        return redirect(url_for(target))

    if request.method == "POST":
        entered = request.form.get("password", "")
        if hmac.compare_digest(entered.encode(), ADMIN_PASSWORD.encode()):
            session["is_admin"] = True
            session["admin_at"] = time.time()
            return redirect(url_for(target))
        time.sleep(1)  # slows down password guessing
        return render_template("admin_login.html", error="Wrong admin password. Try again.")

    return render_template("admin_login.html", error=None)

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_at", None)
    return redirect(url_for("home"))

@app.route("/admin")
def admin_page():
    if not admin_active():
        return redirect(url_for("admin_login"))
    all_orders = database.get_all_orders()
    order_list = []
    for order in all_orders:
        item_names = [products[code]["name"] for code in order["items"] if code in products]
        order_list.append({
            "order_id": order["order_id"],
            "item_list": ", ".join(item_names),
            "total": order["total"],
            "status": order["status"],
            "used": order["used"]
        })
    return render_template("admin.html", order_list=order_list)

if __name__ == "__main__":
    app.run(debug=True)
