# 🤖 IA ASSISTANT - Qualificação Automática de Leads

## 📋 ÍNDICE

1. [O que é](#o-que-é)
2. [Como Funciona](#como-funciona)
3. [Configuração](#configuração)
4. [Personalização](#personalização)
5. [API Endpoints](#api-endpoints)
6. [Custos](#custos)
7. [Exemplos de Uso](#exemplos-de-uso)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 O QUE É

O **IA Assistant** é um sistema de qualificação automática de leads que:

✅ **Responde automaticamente** mensagens no WhatsApp
✅ **Faz perguntas estratégicas** para qualificar leads
✅ **Extrai informações importantes** (nome, interesse, orçamento, prazo)
✅ **Marca leads como qualificados** quando coleta dados suficientes
✅ **Escala para humano** quando necessário
✅ **Totalmente configurável** via JSON

---

## 🔄 COMO FUNCIONA

```
┌─────────────────────────────────────────┐
│  Lead envia mensagem no WhatsApp       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Sistema cria/localiza lead no banco   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  IA Assistant processa mensagem         │
│                                          │
│  • Verifica se quer falar com humano   │
│  • Analisa contexto da conversa        │
│  • Gera próxima pergunta               │
│  • Armazena respostas                  │
│                                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Lead responde todas perguntas?         │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
       SIM           NÃO
        │             │
        ▼             ▼
┌───────────────┐  ┌──────────────┐
│ Qualificado!  │  │ Continua IA  │
│ → Fila        │  │ fazendo      │
│ → Vendedor    │  │ perguntas    │
└───────────────┘  └──────────────┘
```

---

## ⚙️ CONFIGURAÇÃO

### **1. Instalar Dependências**

```bash
cd backend
pip install -r requirements.txt
```

Isso instalará: `openai==1.54.3`

### **2. Obter API Key da OpenAI**

1. Acesse: https://platform.openai.com/api-keys
2. Crie uma conta (ou faça login)
3. Gere uma nova API Key
4. **Importante:** Adicione crédito ($5-10 é suficiente para testar)

### **3. Configurar `.env`**

Edite `/home/user/crmwhatsapp/.env`:

```bash
# IA ASSISTANT
IA_HABILITADA=True
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx  # Sua chave aqui
OPENAI_MODEL=gpt-4o-mini
```

### **4. Iniciar Backend**

```bash
cd backend
python app.py
```

Você verá:
```
✅ Tabelas de IA criadas com sucesso!
✅ Métodos de IA adicionados ao Database!
✅ OpenAI inicializada
🤖 IA Assistant inicializado!
```

---

## 🎨 PERSONALIZAÇÃO

### **Arquivo de Configuração**

`backend/ia_config.json` contém todas as configurações:

```json
{
  "ia_habilitada": true,
  "empresa": "MinhaEmpresa",
  "modelo": "gpt-4o-mini",

  "saudacao": "Olá! 👋 Sou a assistente virtual da {empresa}...",

  "perguntas_qualificacao": [
    {
      "id": "nome",
      "pergunta": "Qual seu nome completo?",
      "obrigatoria": true
    },
    {
      "id": "interesse",
      "pergunta": "Qual produto ou serviço te interessa?",
      "obrigatoria": true
    }
  ],

  "mensagem_qualificado": "Perfeito! Vou conectar você com um especialista...",

  "keywords_humano": [
    "falar com humano",
    "atendente",
    "vendedor"
  ]
}
```

### **Personalizações Comuns**

#### **1. Mudar Nome da Empresa**

```json
"empresa": "SuaEmpresa"
```

#### **2. Adicionar/Remover Perguntas**

```json
"perguntas_qualificacao": [
  {
    "id": "nome",
    "pergunta": "Qual seu nome?",
    "obrigatoria": true
  },
  {
    "id": "cidade",
    "pergunta": "De qual cidade você é?",
    "obrigatoria": false
  }
]
```

#### **3. Mudar Saudação**

```json
"saudacao": "Oi! Sou o robô da {empresa}. Como posso te ajudar hoje?"
```

#### **4. Adicionar Keywords para Humano**

```json
"keywords_humano": [
  "falar com humano",
  "quero uma pessoa",
  "chama o gerente"
]
```

#### **5. Ajustar Comportamento da IA**

```json
"prompt_sistema": "Você é um atendente carismático e descontraído...",
"max_tokens": 200,  // Respostas mais longas
"temperature": 0.9  // Mais criativo (0.1-1.0)
```

---

## 📡 API ENDPOINTS

### **1. Status da IA**

```bash
GET /api/ia/status
```

**Resposta:**
```json
{
  "habilitada": true,
  "configuracao": {
    "ia_habilitada": true,
    "openai_disponivel": true,
    "total_perguntas": 5,
    "modelo": "gpt-4o-mini"
  },
  "estatisticas": {
    "total_interacoes": 45,
    "total_qualificados": 32,
    "total_escalados": 8,
    "taxa_qualificacao": 71.1,
    "media_mensagens_por_lead": 6.2
  }
}
```

### **2. Leads Qualificados pela IA**

```bash
GET /api/ia/leads-qualificados
```

**Resposta:**
```json
[
  {
    "id": 15,
    "name": "João Silva",
    "phone": "5511999999999",
    "status": "qualificado",
    "respostas_coletadas": 5,
    "qualificacao": [
      {
        "pergunta_id": "nome",
        "resposta": "João Silva"
      },
      {
        "pergunta_id": "interesse",
        "resposta": "Site e-commerce"
      }
    ]
  }
]
```

### **3. Ver Qualificação de Um Lead**

```bash
GET /api/leads/15/qualificacao
```

**Resposta:**
```json
{
  "lead_id": 15,
  "total": 5,
  "respostas": [
    {
      "id": 1,
      "pergunta_id": "nome",
      "resposta": "João Silva",
      "created_at": "2025-11-13T14:30:00"
    }
  ]
}
```

### **4. Forçar Escalação para Humano**

```bash
POST /api/ia/forcar-escalacao/15
```

**Resposta:**
```json
{
  "success": true,
  "message": "Lead escalado para atendimento humano"
}
```

---

## 💰 CUSTOS

### **OpenAI GPT-4o-mini** (Recomendado)

| Uso | Custo Aproximado |
|-----|------------------|
| 1 conversa (5-10 mensagens) | $0.01 |
| 100 conversas/dia | $1.00/dia = $30/mês |
| 1000 conversas/dia | $10.00/dia = $300/mês |

### **OpenAI GPT-4o** (Mais inteligente)

| Uso | Custo Aproximado |
|-----|------------------|
| 1 conversa (5-10 mensagens) | $0.05 |
| 100 conversas/dia | $5.00/dia = $150/mês |

### **Modo Fallback** (Sem IA real - Gratuito)

Se não configurar `OPENAI_API_KEY`, o sistema:
- Faz perguntas sequenciais (sem inteligência)
- Não adapta perguntas ao contexto
- Custo: $0

---

## 💬 EXEMPLOS DE USO

### **Conversa Real (IA Habilitada)**

```
Lead: Oi, quero saber sobre sites
IA: Olá! 👋 Sou a assistente virtual da MinhaEmpresa.
    Para te atender melhor, qual seu nome?

Lead: João Silva
IA: Prazer, João! 😊
    Você mencionou interesse em sites. Que tipo de site você precisa?
    (e-commerce, institucional, landing page)

Lead: E-commerce
IA: Ótimo! E-commerce é nossa especialidade.
    Quantos produtos você pretende vender?

Lead: Uns 50
IA: Certo! E qual seu orçamento aproximado?

Lead: Até R$ 5.000
IA: Perfeito, João! ✅

    Resumo:
    • Nome: João Silva
    • Interesse: Site e-commerce
    • Produtos: ~50
    • Orçamento: até R$ 5.000

    Vou te conectar com um especialista agora! 👨‍💼

[Lead vai para fila com status "qualificado"]
```

### **Lead Quer Falar com Humano**

```
Lead: Quero falar com um atendente
IA: Entendido! Vou te conectar com um atendente humano agora.
    Por favor, aguarde um momento. 👨‍💼

[Lead é escalado imediatamente]
```

---

## 🔧 TROUBLESHOOTING

### **Problema: IA não responde**

**Verificar:**
1. `IA_HABILITADA=True` no `.env`
2. `OPENAI_API_KEY` configurada
3. Backend reiniciado após mudança no `.env`

**Teste:**
```bash
curl http://localhost:5000/api/ia/status
```

### **Problema: Erro "OpenAI API key not found"**

**Solução:**
1. Gere chave em: https://platform.openai.com/api-keys
2. Adicione no `.env`:
   ```
   OPENAI_API_KEY=sk-proj-xxxxx
   ```
3. Reinicie backend

### **Problema: Erro "Insufficient quota"**

**Causa:** Sem crédito na conta OpenAI

**Solução:**
1. Acesse: https://platform.openai.com/settings/organization/billing
2. Adicione método de pagamento
3. Compre crédito ($5-10 mínimo)

### **Problema: IA responde coisas estranhas**

**Ajuste o prompt do sistema** em `ia_config.json`:
```json
"prompt_sistema": "Você é um assistente profissional...",
"temperature": 0.5  // Menos criativo
```

### **Problema: IA não coleta informações**

**Verifique se perguntas estão marcadas como obrigatórias:**
```json
{
  "id": "nome",
  "pergunta": "Qual seu nome?",
  "obrigatoria": true  // ← Isso força coleta
}
```

---

## 📊 MONITORAMENTO

### **Ver Estatísticas da IA**

```python
# No Python
from database import Database
from database_ia import extend_database_with_ia

db = Database()
extend_database_with_ia(db)

stats = db.get_estatisticas_ia()
print(stats)
```

**Output:**
```json
{
  "total_interacoes": 150,
  "total_qualificados": 105,
  "total_escalados": 20,
  "taxa_qualificacao": 70.0,
  "media_mensagens_por_lead": 5.8
}
```

### **Ver Leads Qualificados**

```python
leads = db.get_leads_qualificados_ia()
for lead in leads:
    print(f"Lead {lead['id']}: {lead['name']} - {lead['respostas_coletadas']} respostas")
```

---

## 🚀 PRÓXIMAS MELHORIAS

**Planejadas para Versão 2:**

1. **Multi-Cliente**: Config por cliente (já preparado)
2. **Múltiplos Fluxos**: Vendas, Suporte, Agendamento
3. **A/B Testing**: Testar diferentes prompts
4. **IA Aprende**: Aprende com conversas de vendedores
5. **Analytics Avançado**: Dashboard de performance da IA
6. **Integração CRM**: Salesforce, HubSpot, etc

---

## 📞 SUPORTE

**Problemas?**
1. Verificar logs do backend
2. Testar endpoint `/api/ia/status`
3. Verificar crédito OpenAI
4. Revisar `ia_config.json`

**Dúvidas sobre configuração?**
- Todos os campos estão documentados em `ia_config.json`
- Valores padrão funcionam para maioria dos casos

---

**Versão:** 1.0.0
**Data:** 2025-11-13
**Status:** ✅ Pronto para produção
