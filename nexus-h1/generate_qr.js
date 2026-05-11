const QRCode = require('qrcode');
const fs = require('fs');

const qrText = fs.readFileSync('./secrets/whatsapp_qr.txt', 'utf8').trim();

QRCode.toFile('./secrets/whatsapp_qr.png', qrText, {
    width: 400,
    margin: 2
}, (err) => {
    if (err) {
        console.error('Error generating QR:', err);
        process.exit(1);
    }
    console.log('QR code saved to secrets/whatsapp_qr.png');
});