from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

# Generate QR codes for all products automatically on startup (only if missing)
if not os.path.exists("static/product_qr"):
    os.makedirs("static/product_qr")

for code in products:
    qr_path = f"static/product_qr/{code}.png"
    if not os.path.exists(qr_path):
        img = qrcode.make(code)
        img.save(qr_path)

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

@app.route("/payment")
def payment_page():
    cart_codes = session.get("cart", [])
    total = sum(products[code]["price"] for code in cart_codes)
    return render_template("payment.html", total=total)

@app.route("/process_payment", methods=["POST"])
def process_payment():
    data = request.get_json() or {}
    customer_name = data.get("name", "Customer")

    cart_codes = session.get("cart", [])
    total = sum(products[code]["price"] for code in cart_codes)

    order_id = str(uuid.uuid4())[:8]
    signature = hashlib.sha256(f"{order_id}{SECRET_KEY}".encode()).hexdigest()[:12]

    database.save_order(order_id, cart_codes, total, "PAID", signature, False)

    session["cart"] = []
    session["last_order"] = order_id
    session["customer_name"] = customer_name

    return jsonify({"success": True, "order_id": order_id})

@app.route("/receipt")
def receipt_page():
    order_id = session.get("last_order")
    order = database.get_order(order_id) if order_id else None

    if not order:
        return "No recent order found. Please shop first."

    qr_data = f"{order_id}|{order['signature']}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"static/product_qr/receipt_{order_id}.png")

    item_counts = {}
    for code in order["items"]:
        if code in products:
            name = products[code]["name"]
            price = products[code]["price"]
            if name not in item_counts:
                item_counts[name] = {"qty": 0, "price": price}
            item_counts[name]["qty"] += 1

    bill_items = []
    for name, data in item_counts.items():
        bill_items.append({
            "name": name,
            "qty": data["qty"],
            "price": data["price"],
            "subtotal": data["qty"] * data["price"]
        })

    customer_name = session.get("customer_name", "Customer")

    return render_template("receipt.html", order_id=order_id, total=order["total"], qr_filename=f"receipt_{order_id}.png", bill_items=bill_items, customer_name=customer_name)
@app.route("/verify")
def verify_page():
    return render_template("verify.html")

@app.route("/check_order", methods=["POST"])
def check_order():
    data = request.get_json()
    scanned_text = data.get("code")

    try:
        order_id, signature = scanned_text.split("|")
    except:
        return jsonify({"valid": False, "message": "Invalid QR format"})

    order = database.get_order(order_id)

    if not order:
        return jsonify({"valid": False, "message": "❌ Order not found"})

    if order["signature"] != signature:
        return jsonify({"valid": False, "message": "❌ Invalid / tampered QR code"})

    if order["used"]:
        return jsonify({"valid": False, "message": "❌ This QR was already used!"})

    if order["status"] != "PAID":
        return jsonify({"valid": False, "message": "❌ Order not paid"})

        database.mark_order_used(order_id)

    item_counts = {}
    for code in order["items"]:
        if code in products:
            name = products[code]["name"]
            if name not in item_counts:
                item_counts[name] = 0
            item_counts[name] += 1

    item_list = [f"{name} x{qty}" for name, qty in item_counts.items()]

    if random.random() < 0.2:
        return jsonify({"valid": True, "flagged": True, "order_id": order_id, "total": order["total"], "items": item_list, "message": "⚠️ FLAGGED for random check — please show bag contents to staff."})

    return jsonify({"valid": True, "flagged": False, "order_id": order_id, "total": order["total"], "items": item_list, "message": "✅ Verified — Allow Exit"})
@app.route("/admin")
def admin_page():
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
@app.route("/remove_from_cart/<int:index>")
def remove_from_cart(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session["cart"] = cart
        session.modified = True
    return redirect(url_for("view_cart"))

if __name__ == "__main__":
    app.run(debug=True)