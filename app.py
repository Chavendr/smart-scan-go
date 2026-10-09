from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import hashlib
import random
import database
import qrcode
import os

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

# ---------------- Login check (runs before every page) ----------------

@app.before_request
def require_login():
    open_pages = ["home", "login", "signup", "logout", "static"]
    if request.endpoint in open_pages:
        return None
    if not session.get("user_id"):
        if request.method == "POST":
            return jsonify({"success": False, "valid": False, "message": "Please log in first."}), 401
        return redirect(url_for("login"))

# ---------------- Pages ----------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def show_products():
    categories = {}
    for code, info in products.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((code, info))
    return render_template("products.html", categories=categories)

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

if __name__ == "__main__":
    app.run(debug=True)