from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (64, 64), "#1a1a2e")
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("seguiemj.ttf", 40)  # Windows emoji font
    draw.text((8, 8), "🛒", font=font, embedded_color=True)
except:
    draw.rectangle([16, 20, 48, 44], fill="#ff7e2e")  # fallback: simple orange cart shape

img.save("static/favicon.png")
print("Favicon created!")