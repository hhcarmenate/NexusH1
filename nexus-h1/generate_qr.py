import qrcode

with open('secrets/whatsapp_qr.txt', 'r') as f:
    qr_text = f.read().strip()

qr = qrcode.QRCode(version=1, box_size=10, border=2)
qr.add_data(qr_text)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save('secrets/whatsapp_qr.png')
print("QR code saved to secrets/whatsapp_qr.png")