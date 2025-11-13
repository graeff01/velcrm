# 🚀 CRM WHATSAPP - GUIA DE INÍCIO RÁPIDO (PILOTO)

## ✅ CORREÇÕES DE SEGURANÇA APLICADAS

Todas as 6 vulnerabilidades críticas foram corrigidas:

1. ✅ **SECRET_KEY segura** - Gerada e armazenada em `.env`
2. ✅ **Bcrypt implementado** - Substituiu SHA256 (migração automática)
3. ✅ **CORS restrito** - Apenas domínios autorizados
4. ✅ **Sessões WhatsApp protegidas** - `.gitignore` atualizado
5. ✅ **Banco de dados inicializado** - 88KB com usuário admin
6. ✅ **Backup automático** - Script criado e testado

---

## 🎯 INÍCIO RÁPIDO (3 PASSOS)

### 1️⃣ Instalar Dependências

```bash
# Backend
cd backend
pip3 install -r requirements.txt

# WhatsApp Service
cd ../whatsapp-service
npm install

# Frontend
cd ../frontend
npm install
```

### 2️⃣ Iniciar Serviços

**Terminal 1 - Backend:**
```bash
cd backend
python3 app.py
```
✅ Deve mostrar: `🚀 CRM WhatsApp iniciado com todas as melhorias!`

**Terminal 2 - WhatsApp Service:**
```bash
cd whatsapp-service
npm start
```
✅ Escaneie o QR Code com WhatsApp

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```
✅ Acesse: http://localhost:3000

### 3️⃣ Login Inicial

**Credenciais padrão:**
- Usuário: `admin`
- Senha: `admin123`

⚠️ **IMPORTANTE:** Troque a senha imediatamente após primeiro login!

---

## 🔐 AÇÕES OBRIGATÓRIAS ANTES DO PILOTO

### 1. Trocar Senha Admin

```python
# Método 1: Via Python
cd backend
python3 -c "from database import Database; db = Database(); db.change_user_password(1, 'SenhaSuperForte@2024'); print('✅ Senha alterada')"
```

### 2. Configurar Domínio (Produção)

Editar `.env`:
```bash
CORS_ORIGINS=https://seudominio.com
```

### 3. Configurar Backup Automático

```bash
# Testar backup manual
./backup_database.sh

# Configurar cron (diário às 2h)
crontab -e
# Adicionar: 0 2 * * * /home/user/crmwhatsapp/backup_database.sh
```

---

## 📊 ARQUITETURA

```
┌─────────────────┐
│   FRONTEND      │  React + Socket.io
│  (Porta 3000)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    BACKEND      │  Flask + Socket.io
│  (Porta 5000)   │  SQLite (88KB)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WHATSAPP SERVICE│  Baileys/Venom
│  (Porta 3001)   │  Node.js
└─────────────────┘
```

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
crmwhatsapp/
├── .env                      ✅ SECRET_KEY e configs
├── backend/
│   ├── .env                  ✅ Google Sheets desabilitado
│   ├── app.py               ✅ Lê SECRET_KEY de .env
│   ├── database.py          ✅ Bcrypt implementado
│   ├── crm_whatsapp.db      ✅ Banco inicializado (88KB)
│   └── requirements.txt     ✅ Bcrypt adicionado
├── whatsapp-service/
│   ├── .env                  ✅ Webhook configurado
│   ├── index.js
│   └── package.json
├── frontend/
│   └── src/
├── backups/                  ✅ Backup criado
│   └── crm_backup_*.db.gz
├── backup_database.sh        ✅ Script de backup
├── DEPLOY.md                 📖 Guia de deploy
├── SECURITY.md               🔐 Guia de segurança
└── README_PILOTO.md          👈 Você está aqui
```

---

## 🧪 TESTAR FUNCIONALIDADES

### 1. Criar Usuário Vendedor
```bash
# Via API (após login como admin)
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "vendedor1",
    "password": "senha123",
    "name": "João Vendedor",
    "role": "vendedor"
  }'
```

### 2. Simular Mensagem WhatsApp
```bash
curl -X POST http://localhost:5000/api/simulate/message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5511999999999",
    "name": "Cliente Teste",
    "content": "Olá, gostaria de mais informações"
  }'
```

### 3. Verificar Health Check
```bash
curl http://localhost:5000/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "whatsapp": "connected",
    "google_sheets": "disconnected"
  }
}
```

---

## 📈 MÉTRICAS E DASHBOARDS

### Endpoints Principais:
- **Dashboard:** http://localhost:3000
- **Métricas:** http://localhost:5000/api/metrics
- **Alertas:** http://localhost:3000/alerts
- **Kanban:** http://localhost:3000/kanban

### Funcionalidades Disponíveis:
✅ Chat em tempo real via WhatsApp
✅ Gestão de leads (fila, atribuição, status)
✅ Métricas de conversão e SLA
✅ Sistema de alertas (leads abandonados, SLA)
✅ Auditoria completa de ações
✅ Tags personalizadas
✅ Transferência de leads
✅ Notas internas
✅ Ranking de vendedores

---

## 🚨 TROUBLESHOOTING

### Erro: "ModuleNotFoundError: No module named 'bcrypt'"
```bash
cd backend
pip3 install bcrypt
```

### Erro: "Database is locked"
```bash
# Fechar todos os processos que usam o banco
pkill -f "python3 app.py"
rm -f backend/*.db-journal
```

### WhatsApp não conecta:
```bash
# Deletar sessão antiga
rm -rf auth_info_baileys/*
# Reiniciar whatsapp-service
cd whatsapp-service
npm start
# Escanear novo QR Code
```

### Frontend não carrega:
```bash
# Limpar cache e reinstalar
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## 📋 CHECKLIST PILOTO

### Pré-Lançamento:
- [ ] Dependências instaladas (backend, whatsapp-service, frontend)
- [ ] Banco de dados inicializado (88KB)
- [ ] Senha admin alterada
- [ ] WhatsApp conectado (QR Code escaneado)
- [ ] Backup testado
- [ ] Health check retorna "healthy"

### Primeiro Uso:
- [ ] Login como admin realizado
- [ ] Usuário vendedor criado
- [ ] Lead de teste criado
- [ ] Mensagem enviada/recebida
- [ ] Dashboard acessado
- [ ] Métricas carregando

### Monitoramento:
- [ ] Logs de auditoria funcionando
- [ ] Alertas de SLA ativos
- [ ] Socket.io conectado
- [ ] Backup automático agendado

---

## 🎓 PRÓXIMOS PASSOS

### Semana 1 (Piloto):
1. Conectar WhatsApp real
2. Criar 2-3 usuários (admin, gestor, vendedor)
3. Testar com 5-10 leads reais
4. Monitorar logs e erros
5. Ajustar alertas de SLA

### Semana 2-4 (Ajustes):
1. Coletar feedbacks dos usuários
2. Ajustar interface conforme necessidade
3. Otimizar alertas e notificações
4. Adicionar tags personalizadas
5. Treinar equipe

### Mês 2 (Expansão):
1. Migrar SQLite → PostgreSQL (se necessário)
2. Implementar Redis para cache
3. Adicionar testes automatizados
4. Configurar monitoramento (Sentry)
5. Documentar processos

---

## 📞 SUPORTE

### Documentação:
- **Deploy:** Ver `DEPLOY.md`
- **Segurança:** Ver `SECURITY.md`

### Comandos Úteis:
```bash
# Ver logs backend
tail -f backend/app.log

# Ver processos
ps aux | grep -E "python3|node"

# Reiniciar tudo
pkill -f "python3 app.py"
pkill -f "node index.js"
```

---

## 🎉 VOCÊ ESTÁ PRONTO!

Seu CRM WhatsApp está configurado e seguro para piloto.

**Próximo passo:** Conecte seu WhatsApp real e teste com leads!

---

**Versão:** 1.0.0 (Piloto)
**Data:** 2025-11-13
**Status:** ✅ Pronto para piloto
