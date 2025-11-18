const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const express = require('express');
const axios = require('axios');
const cors = require('cors');
const P = require('pino');

const app = express();
app.use(express.json());
app.use(cors());

let sock = null;
let isConnected = false;
const logger = P({ level: 'silent' });

async function connectToWhatsApp() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
        const { version } = await fetchLatestBaileysVersion();
        
        sock = makeWASocket({
            version,
            logger,
            auth: state,
            browser: ['CRM Veloce', 'Chrome', '10.0']
            // ❌ REMOVIDO: printQRInTerminal
        });

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            // ✅ ADICIONAR MANUALMENTE O QR CODE
            if (qr) {
                console.log('\n📱 ESCANEIE O QR CODE NO SEU WHATSAPP:\n');
                const qrcode = require('qrcode-terminal');
                qrcode.generate(qr, { small: true });
                console.log('\n');
            }
            
            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`🔄 Conexão fechada. Reconectar: ${shouldReconnect}`);
                if (shouldReconnect) {
                    setTimeout(() => connectToWhatsApp(), 3000);
                }
                isConnected = false;
            } else if (connection === 'open') {
                console.log('✅ WhatsApp conectado com sucesso!');
                isConnected = true;
            }
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('messages.upsert', async (m) => {
            try {
                const message = m.messages[0];
                if (!message.message || message.key.fromMe || message.key.remoteJid.includes('@g.us')) return;

                const phone = message.key.remoteJid.replace('@s.whatsapp.net', '');
                const name = message.pushName || 'Lead';
                let content = message.message.conversation || 
                             message.message.extendedTextMessage?.text || 
                             '[Mensagem não suportada]';

                console.log(`📨 ${name} (${phone}): ${content}`);

await axios.post('http://localhost:5000/api/webhook/message', {                    phone, 
                    message: content, 
                    name,
                    timestamp: new Date().toISOString()
                }, {
                    timeout: 5000
                });
                
                console.log('✅ Mensagem encaminhada para backend');
            } catch (error) {
                console.error('❌ Erro ao processar mensagem:', error.message);
            }
        });
    } catch (error) {
        console.error('❌ Erro ao conectar:', error.message);
        setTimeout(() => connectToWhatsApp(), 5000);
    }
}

app.post('/send', async (req, res) => {
    try {
        const { phone, message } = req.body;
        
        if (!sock || !isConnected) {
            console.error('❌ WhatsApp não conectado');
            return res.status(503).json({ 
                success: false, 
                error: 'WhatsApp não conectado' 
            });
        }

        let jid = phone;
        if (!jid.includes('@s.whatsapp.net')) {
            jid = jid.replace(/\D/g, '') + '@s.whatsapp.net';
        }
        
        console.log(`📤 Enviando para ${phone}...`);
        await sock.sendMessage(jid, { text: message });
        console.log(`✅ Mensagem enviada!`);
        
        res.json({ success: true });
    } catch (error) {
        console.error('❌ Erro ao enviar:', error.message);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

app.get('/status', (req, res) => {
    res.json({ 
        connected: isConnected,
        service: 'baileys',
        timestamp: new Date().toISOString()
    });
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log('🚀 Servidor Baileys iniciado');
    console.log(`📡 Porta: ${PORT}`);
    console.log('🔌 Conectando ao WhatsApp...\n');
    connectToWhatsApp();
});

process.on('SIGINT', async () => {
    console.log('\n👋 Desconectando...');
    if (sock) {
        await sock.logout();
    }
    process.exit(0);
});