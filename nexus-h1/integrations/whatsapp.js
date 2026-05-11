const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');

const SESSION_PATH = path.join(__dirname, '..', 'secrets', 'whatsapp_session');

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: SESSION_PATH }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Message queue for incoming messages
let messageQueue = [];
let isReady = false;

client.on('qr', (qr) => {
    console.log('QR_RECEIVED');
    console.log(qr);
    // Save QR to file for external scanning
    fs.writeFileSync(path.join(__dirname, '..', 'secrets', 'whatsapp_qr.txt'), qr);
});

client.on('ready', () => {
    isReady = true;
    console.log('WHATSAPP_READY');
});

client.on('message', async (msg) => {
    // Ignore own messages and status broadcasts
    if (msg.fromMe || msg.from === 'status@broadcast') return;
    
    const messageData = {
        id: msg.id.id,
        from: msg.from,
        fromMe: msg.fromMe,
        body: msg.body,
        timestamp: msg.timestamp,
        type: msg.type,
        hasMedia: msg.hasMedia,
        author: msg.author || msg.from
    };
    
    messageQueue.push(messageData);
    
    // Also append to log file
    const logEntry = `[${new Date().toISOString()}] ${msg.from}: ${msg.body}\n`;
    fs.appendFileSync(path.join(__dirname, '..', 'memory', 'whatsapp_messages.log'), logEntry);
    
    console.log('MESSAGE_RECEIVED', JSON.stringify(messageData));
});

client.on('disconnected', (reason) => {
    isReady = false;
    console.log('WHATSAPP_DISCONNECTED', reason);
});

// Command interface via stdin
process.stdin.on('data', async (data) => {
    const line = data.toString().trim();
    if (!line) return;
    
    try {
        const cmd = JSON.parse(line);
        
        switch (cmd.action) {
            case 'send': {
                const { to, message } = cmd;
                const chatId = to.includes('@c.us') ? to : `${to}@c.us`;
                const sent = await client.sendMessage(chatId, message);
                console.log('SENT', JSON.stringify({ id: sent.id.id, to }));
                break;
            }
            case 'send_media': {
                const { to, path: mediaPath, caption } = cmd;
                const chatId = to.includes('@c.us') ? to : `${to}@c.us`;
                const media = require('whatsapp-web.js').MessageMedia.fromFilePath(mediaPath);
                const sent = await client.sendMessage(chatId, media, { caption });
                console.log('SENT_MEDIA', JSON.stringify({ id: sent.id.id, to }));
                break;
            }
            case 'get_chats': {
                const chats = await client.getChats();
                const simplified = chats.slice(0, 50).map(c => ({
                    id: c.id._serialized,
                    name: c.name,
                    isGroup: c.isGroup,
                    unreadCount: c.unreadCount,
                    timestamp: c.timestamp
                }));
                console.log('CHATS', JSON.stringify(simplified));
                break;
            }
            case 'get_messages': {
                const { chatId, limit = 50 } = cmd;
                const chat = await client.getChatById(chatId);
                const messages = await chat.fetchMessages({ limit });
                const simplified = messages.map(m => ({
                    id: m.id.id,
                    from: m.from,
                    body: m.body,
                    timestamp: m.timestamp,
                    fromMe: m.fromMe
                }));
                console.log('MESSAGES', JSON.stringify(simplified));
                break;
            }
            case 'status': {
                console.log('STATUS', JSON.stringify({ ready: isReady, queueSize: messageQueue.length }));
                break;
            }
            case 'get_queue': {
                console.log('QUEUE', JSON.stringify(messageQueue));
                messageQueue = []; // clear after reading
                break;
            }
            default:
                console.log('ERROR', 'Unknown action:', cmd.action);
        }
    } catch (err) {
        console.log('ERROR', err.message);
    }
});

client.initialize();
