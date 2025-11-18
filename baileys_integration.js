const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const express = require('express');
const axios = require('axios');
const cors = require('cors');
const P = require('pino');
const qrcode = require('qrcode-terminal');

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
            browser: ['CRM WhatsApp', 'Chrome', '10.0']
        });

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('\n📱 ESCANEIE O QR CODE:\n');
                qrcode.generate(qr, { small: true });
                console.log('\n');
            }
            
            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`🔄 Conexão fechada. Reconectar: ${shouldReconnect}`);
                isConnected = false;
                if (shouldReconnect) {
                    setTimeout(() => connectToWhatsApp(), 3000);
                }
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

                // ✅ URL CORRIGIDA
                await axios.post('http://localhost:5000/api/webhook/message', {
                    phone,
                    content,
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

        // Remove tudo exceto números
        let phoneNumbers = phone.replace(/\D/g, '');
        
        // Garante DDI 55
        if (!phoneNumbers.startsWith('55')) {
            phoneNumbers = '55' + phoneNumbers;
        }
        
        // ✅ VALIDAÇÃO DE CELULAR BRASILEIRO
        // Formato: 55 + DDD (2) + número (8 ou 9 dígitos)
        if (phoneNumbers.length < 12 || phoneNumbers.length > 13) {
            console.error(`❌ Número inválido: ${phoneNumbers} (deve ter 12 ou 13 dígitos)`);
            return res.status(400).json({ 
                success: false, 
                error: 'Número de telefone inválido' 
            });
        }
        
        // Formata JID
        let jid = phoneNumbers + '@s.whatsapp.net';
        
        // Log detalhado
        const ddi = phoneNumbers.slice(0, 2);
        const ddd = phoneNumbers.slice(2, 4);
        const numero = phoneNumbers.slice(4);
        console.log(`📤 Enviando para: +${ddi} ${ddd} ${numero}`);
        console.log(`   JID: ${jid}`);
        console.log(`   Comprimento: ${phoneNumbers.length} dígitos`);
        
        // ✅ IMPORTANTE: Verifica se o número existe no WhatsApp
        try {
            const [result] = await sock.onWhatsApp(jid);
            if (!result || !result.exists) {
                console.error(`❌ Número não existe no WhatsApp: ${jid}`);
                return res.status(404).json({ 
                    success: false, 
                    error: 'Número não encontrado no WhatsApp' 
                });
            }
            console.log(`✅ Número verificado: ${result.jid}`);
        } catch (verifyError) {
            console.error(`⚠️ Não foi possível verificar número: ${verifyError.message}`);
        }
        
        // Envia mensagem
        await sock.sendMessage(jid, { text: message });
        console.log(`✅ Mensagem enviada com sucesso!`);
        
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