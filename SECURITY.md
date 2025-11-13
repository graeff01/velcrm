# 🔐 GUIA DE SEGURANÇA - CRM WHATSAPP

## ⚠️ CORREÇÕES CRÍTICAS APLICADAS

### ✅ 1. SECRET_KEY Segura
**ANTES (INSEGURO):**
```python
app.config["SECRET_KEY"] = "sua-chave-secreta-aqui-mude-em-producao"
```

**DEPOIS (SEGURO):**
```python
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback-insecure-key-change-immediately")
```

**Arquivo `.env`:**
```bash
SECRET_KEY=e9de68e7662cc52e6689d9fd3592a9298964a6fdcca552cba28011de8d11be52
```

**Impacto:** Previne session hijacking e CSRF attacks.

---

### ✅ 2. Hash bcrypt (Substituiu SHA256)
**ANTES (VULNERÁVEL):**
```python
def hash_password(self, password):
    return hashlib.sha256(password.encode()).hexdigest()
```

**DEPOIS (SEGURO):**
```python
def hash_password(self, password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')
```

**Impacto:** SHA256 é rápido demais → vulnerável a ataques de força bruta. Bcrypt tem custo computacional alto, tornando ataques impraticáveis.

**Migração automática:** Senhas antigas SHA256 são migradas para bcrypt no primeiro login.

---

### ✅ 3. CORS Restrito
**ANTES (PERIGOSO):**
```python
socketio = SocketIO(app, cors_allowed_origins="*")
```

**DEPOIS (SEGURO):**
```python
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
socketio = SocketIO(app, cors_allowed_origins=cors_origins)
```

**Impacto:** Apenas domínios autorizados podem fazer requisições.

---

### ✅ 4. Sessões WhatsApp Protegidas
**Arquivo `.gitignore`:**
```
auth_info_baileys/
tokens/
sessions/
creds.json
```

**Impacto:** Previne vazamento de credenciais WhatsApp que permitiriam clonagem da conta.

---

### ✅ 5. Backup Automático
**Script:** `backup_database.sh`
- Backup diário comprimido
- Retenção de 30 dias
- Verificação de integridade

**Impacto:** Previne perda de dados em caso de corrupção ou ataque.

---

## 🚨 AÇÕES OBRIGATÓRIAS ANTES DO PILOTO

### 1. Trocar Senha Admin Padrão
**CRÍTICO:** A senha padrão é `admin/admin123`

```python
# Método 1: Via Python
from database import Database
db = Database()
db.change_user_password(1, "SenhaForte@2024!Crm")
print("✅ Senha alterada")
```

Ou via API (após login):
```bash
curl -X PUT http://localhost:5000/api/users/1/password \
  -H "Content-Type: application/json" \
  -d '{"new_password": "SenhaForte@2024!Crm"}'
```

---

### 2. Configurar HTTPS (Produção)
```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d seudominio.com
```

**Atualizar `.env`:**
```
SESSION_COOKIE_SECURE=True
```

---

### 3. Configurar Firewall
```bash
# Permitir apenas portas necessárias
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Bloquear portas internas
sudo ufw deny 5000/tcp   # Backend (acessar via Nginx)
sudo ufw deny 3001/tcp   # WhatsApp service (interno)
```

---

### 4. Limitar Taxa de Requisições
**Já implementado em `middlewares.py`:**
- 60 requisições/minuto
- 1000 requisições/hora

**Para produção (usar Redis):**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

---

## 🔒 MELHORES PRÁTICAS

### Senhas Fortes
**Política recomendada:**
- Mínimo 12 caracteres
- Letras maiúsculas e minúsculas
- Números
- Caracteres especiais

**Implementar validação:**
```python
import re

def is_strong_password(password):
    if len(password) < 12:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False
    return True
```

---

### Rotação de SECRET_KEY
**A cada 90 dias:**
```bash
# Gerar nova chave
python3 -c "import secrets; print(secrets.token_hex(32))"

# Atualizar .env
# Reiniciar serviços
```

---

### Auditoria Regular
```python
# Verificar logins suspeitos
from database import Database
db = Database()
logs = db.get_audit_logs(limit=500)

# Analisar tentativas de login falhadas
failed_logins = [l for l in logs if l['action'] == 'login_failed']
```

---

### Monitoramento de Sessões
```bash
# Ver sessões ativas (via PM2)
pm2 monit

# Ver logs de auditoria
tail -f backend/audit.log
```

---

## 🛡️ PROTEÇÕES IMPLEMENTADAS

### 1. SQL Injection
✅ Queries parametrizadas em todas as operações
```python
c.execute("SELECT * FROM users WHERE username = ?", (username,))
```

### 2. XSS (Cross-Site Scripting)
✅ Sanitização de HTML em inputs
```python
validator.sanitize_html(content)
```

### 3. CSRF (Cross-Site Request Forgery)
✅ Session-based auth + CORS restrito

### 4. Rate Limiting
✅ Middleware implementado (60 req/min)

### 5. Validação de Inputs
✅ InputValidator em todos os endpoints críticos

### 6. Logs de Auditoria
✅ Todas as ações registradas em `audit_log`

### 7. Security Headers
✅ Middleware `add_security_headers`:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (HSTS)

---

## 🚫 VULNERABILIDADES CORRIGIDAS

| Vulnerabilidade | Severidade | Status |
|----------------|------------|--------|
| SECRET_KEY hardcoded | 🔴 Crítico | ✅ Corrigido |
| Hash SHA256 | 🔴 Crítico | ✅ Migrado para bcrypt |
| CORS aberto | 🔴 Crítico | ✅ Restrito |
| Sessões WhatsApp expostas | 🔴 Crítico | ✅ .gitignore atualizado |
| Banco vazio | 🟡 Alto | ✅ Inicializado |
| Senha admin padrão | 🟡 Alto | ⚠️ Trocar manualmente |
| Rate limiting em memória | 🟡 Médio | ⚠️ Migrar para Redis |
| Sem backup | 🟡 Médio | ✅ Script criado |

---

## 📋 CHECKLIST DE SEGURANÇA

### Pré-Deploy:
- [ ] SECRET_KEY única gerada
- [ ] Senha admin alterada
- [ ] `.env` criado e populado
- [ ] Backup automático configurado
- [ ] CORS configurado para domínio correto

### Pós-Deploy:
- [ ] HTTPS habilitado
- [ ] Firewall configurado
- [ ] Certificado SSL válido
- [ ] Logs de auditoria monitorados
- [ ] Backup testado e verificado

### Manutenção:
- [ ] Atualizar dependências mensalmente
- [ ] Revisar logs de auditoria semanalmente
- [ ] Rotacionar SECRET_KEY a cada 90 dias
- [ ] Testar restauração de backup mensalmente
- [ ] Verificar usuários inativos a cada 30 dias

---

## 🔍 TESTES DE SEGURANÇA

### 1. Testar Rate Limiting:
```bash
# Deve retornar 429 após 60 requisições/minuto
for i in {1..70}; do curl http://localhost:5000/api/leads; done
```

### 2. Testar CORS:
```bash
# Deve bloquear origem não autorizada
curl -H "Origin: http://malicious.com" http://localhost:5000/api/leads
```

### 3. Testar SQL Injection:
```bash
# Deve retornar erro de validação
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'"'"' OR 1=1--", "password": "test"}'
```

---

## 📞 CONTATO SEGURANÇA

Em caso de vulnerabilidade descoberta:
1. NÃO publicar em issues públicas
2. Enviar email para: security@seudominio.com
3. Aguardar confirmação (48h)

---

**Última revisão de segurança:** 2025-11-13
**Próxima revisão:** 2025-12-13
