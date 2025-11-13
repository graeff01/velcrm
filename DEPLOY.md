# 🚀 GUIA DE DEPLOY - CRM WHATSAPP

## ✅ PRÉ-REQUISITOS

### Sistema:
- Ubuntu/Debian Linux
- Python 3.8+
- Node.js 16+
- Git

### Dependências:
```bash
sudo apt update
sudo apt install python3-pip nodejs npm
```

---

## 📋 CHECKLIST PRÉ-PILOTO

### 1. Variáveis de Ambiente
- [ ] Arquivo `.env` criado na raiz
- [ ] `SECRET_KEY` gerada com segurança (nunca usar default!)
- [ ] `CORS_ORIGINS` configurado para domínio correto
- [ ] Credenciais Google Sheets (se usar)

### 2. Segurança
- [ ] Trocar senha admin padrão (admin/admin123)
- [ ] Habilitar HTTPS em produção
- [ ] Configurar firewall (portas 5000, 3000, 3001)
- [ ] Backup automático configurado
- [ ] Nunca commitar `.env` ou `auth_info_baileys/`

### 3. Banco de Dados
- [ ] Banco inicializado (`crm_whatsapp.db` criado)
- [ ] Usuários criados (admin, gestor, vendedor)
- [ ] Backup testado

---

## 🔐 CONFIGURAÇÃO DE SEGURANÇA

### 1. Gerar SECRET_KEY forte:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Adicionar ao `.env`:
```
SECRET_KEY=sua-chave-aqui
```

### 2. Trocar senha admin:
```python
# Conectar no Python
from database import Database
db = Database()
db.change_user_password(1, "nova_senha_forte_123!")
```

### 3. Configurar CORS para produção:
```env
CORS_ORIGINS=https://seudominio.com,https://app.seudominio.com
```

---

## 📦 INSTALAÇÃO

### 1. Clonar repositório:
```bash
git clone https://github.com/seu-usuario/crmwhatsapp.git
cd crmwhatsapp
```

### 2. Backend:
```bash
cd backend
pip3 install -r requirements.txt
python3 app.py
```

### 3. WhatsApp Service:
```bash
cd whatsapp-service
npm install
npm start
```

### 4. Frontend:
```bash
cd frontend
npm install
npm run dev  # Desenvolvimento
npm run build  # Produção
```

---

## 🔄 BACKUP AUTOMÁTICO

### Configurar cron para backup diário às 2h:
```bash
crontab -e
```

Adicionar:
```
0 2 * * * /home/user/crmwhatsapp/backup_database.sh
```

### Backup manual:
```bash
./backup_database.sh
```

### Restaurar backup:
```bash
gunzip -c backups/crm_backup_YYYYMMDD_HHMMSS.db.gz > backend/crm_whatsapp.db
```

---

## 🌐 DEPLOY EM PRODUÇÃO

### Opção 1: PM2 (Recomendado)
```bash
# Instalar PM2
npm install -g pm2

# Backend
cd backend
pm2 start app.py --name crm-backend --interpreter python3

# WhatsApp Service
cd ../whatsapp-service
pm2 start index.js --name whatsapp-service

# Frontend (se não usar Nginx)
cd ../frontend
npm run build
pm2 serve build 3000 --name crm-frontend

# Salvar configuração
pm2 save
pm2 startup
```

### Opção 2: Systemd
Criar arquivos em `/etc/systemd/system/`:

**crm-backend.service:**
```ini
[Unit]
Description=CRM WhatsApp Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/crmwhatsapp/backend
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Habilitar:
```bash
sudo systemctl enable crm-backend
sudo systemctl start crm-backend
```

### Opção 3: Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name seudominio.com;

    # Backend API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Socket.io
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }

    # Frontend
    location / {
        root /home/user/crmwhatsapp/frontend/build;
        try_files $uri /index.html;
    }
}
```

---

## 🔍 MONITORAMENTO

### Health Check:
```bash
curl http://localhost:5000/health
```

### Logs:
```bash
# PM2
pm2 logs crm-backend
pm2 logs whatsapp-service

# Systemd
journalctl -u crm-backend -f
```

### Métricas:
- Acessar: http://localhost:5000/api/metrics
- Dashboard de alertas: Frontend → Alertas

---

## 🚨 TROUBLESHOOTING

### Banco de dados vazio:
```bash
cd backend
python3 -c "from database import Database; db = Database(); print('✅ Banco inicializado')"
```

### WhatsApp não conecta:
1. Deletar `auth_info_baileys/`
2. Reiniciar `whatsapp-service`
3. Escanear QR Code

### CORS bloqueado:
Verificar `.env`:
```
CORS_ORIGINS=http://localhost:3000
```

### Erro de módulo Python:
```bash
pip3 install -r requirements.txt --upgrade
```

---

## 📊 MIGRAÇÃO DE DADOS

### Exportar dados:
```bash
sqlite3 backend/crm_whatsapp.db .dump > backup.sql
```

### Importar dados:
```bash
sqlite3 backend/crm_whatsapp.db < backup.sql
```

---

## 🔒 SEGURANÇA CHECKLIST

- [ ] SECRET_KEY única e forte
- [ ] Senha admin alterada
- [ ] HTTPS habilitado (Let's Encrypt)
- [ ] Firewall configurado
- [ ] Backup automático ativo
- [ ] `.env` no `.gitignore`
- [ ] `auth_info_baileys/` no `.gitignore`
- [ ] Rate limiting ativo
- [ ] Logs de auditoria habilitados

---

## 📞 SUPORTE

Em caso de problemas:
1. Verificar logs (`pm2 logs` ou `journalctl`)
2. Testar health check (`curl http://localhost:5000/health`)
3. Verificar portas (`netstat -tulpn | grep -E '5000|3000|3001'`)
4. Revisar `.env` e configurações

---

**Última atualização:** 2025-11-13
