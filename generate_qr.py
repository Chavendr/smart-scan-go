import qrcode

products = ["PROD001", "PROD002", "PROD003"]

for code in products:
    img = qrcode.make(code)
    img.save(f"static/product_qr/{code}.png")
    print(f"Created QR for {code}")