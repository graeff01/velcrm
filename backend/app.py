from flask import Flask, request, jsonify, session
from flask_socketio import SocketIO, join_room, leave_room
from flask_cors import CORS
from notification_service import NotificationService
from database import Database
from whatsapp_service import WhatsAppService
from middlewares import (
    rate_limit, validate_request, handle_errors,
    InputValidator, add_security_headers, AuditLogger
)
from utils import Paginator, MessageSearcher, LeadSearcher, PerformanceCache
import asyncio
from functools import wraps
from database_tags_sla import extend_database_with_tags_sla
from database_ia import extend_database_with_ia
from ia_assistant import IAAssistant
from datetime import datetime
from advanced_cache import cached, invalidate_cache, get_cache_stats
from alert_system import AlertSystem
from alert_monitoring_service import AlertMonitoringService, check_alerts_once
from gestor_whatsapp_notifier import GestorWhatsAppNotifier
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# =======================
# CONFIGURAÇÃO PRINCIPAL
# =======================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback-insecure-key-change-immediately")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

# CORS - Usar variável de ambiente para produção
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
CORS(app, supports_credentials=True, origins=cors_origins)

socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode="threading")

# Inicializar serviço de notificações
notification_service = NotificationService(socketio)

# Inicialização dos serviços
db = Database()
extend_database_with_tags_sla(db)
extend_database_with_ia(db)  # 🤖 Adicionar tabelas de IA
whatsapp = WhatsAppService(db, socketio)
validator = InputValidator()
audit_logger = AuditLogger(db)

# 🤖 Inicializar IA Assistant
ia_assistant = None
if os.getenv("IA_HABILITADA", "True") == "True":
    try:
        ia_assistant = IAAssistant(db)
        print("🤖 IA Assistant inicializado!")
    except Exception as e:
        print(f"⚠️ IA Assistant desabilitado: {e}")

# Utilitários
message_searcher = MessageSearcher(db)
lead_searcher = LeadSearcher(db)
cache = PerformanceCache(ttl_seconds=300)

print("🚀 CRM WhatsApp iniciado com todas as melhorias!")

# 🚨 Inicializar sistema de alertas
alert_monitoring = AlertMonitoringService(
    db=db,
    socketio=socketio,
    notification_service=notification_service,
    whatsapp_service=whatsapp,
    check_interval=300  # Verifica a cada 5 minutos
)

# Iniciar monitoramento em background
alert_monitoring.start()

# =======================
# MIDDLEWARE GLOBAL
# =======================
@app.after_request
def after_request(response):
    return add_security_headers(response)

# =======================
# DECORATORS DE SEGURANÇA
# =======================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Não autenticado"}), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Não autenticado"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Sem permissão"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ========================================
# GOOGLE SHEETS INTEGRATION
# ========================================

from banco.google_sheets_service import GoogleSheetsService

# Inicializar Google Sheets
sheets_service = None
if os.getenv('GOOGLE_SHEETS_ENABLED') == 'True':
    try:
        sheets_service = GoogleSheetsService(
            credentials_path=os.getenv('GOOGLE_SHEETS_CREDENTIALS'),
            spreadsheet_id=os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        )
        
        # ⚠️ EXECUTAR APENAS UMA VEZ (primeira configuração)
        # sheets_service.setup_spreadsheet()
        
        # Testar conexão
        if sheets_service.test_connection():
            print("✅ Google Sheets integrado com sucesso!")
            print(f"📊 Planilha: {sheets_service.get_spreadsheet_url()}")
        
    except Exception as e:
        print(f"⚠️ Google Sheets desabilitado: {e}")
        sheets_service = None


# =======================
# HELPER: SINCRONIZAR COM SHEETS
# =======================
def sync_lead_to_sheets(lead_id):
    """Sincroniza um lead com o Google Sheets"""
    if not sheets_service:
        return
    
    try:
        lead = db.get_lead(lead_id)
        if lead:
            lead['tags'] = db.get_lead_tags(lead_id)
            sheets_service.sync_lead(lead)
            print(f"📊 Lead {lead_id} sincronizado com Sheets")
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar lead {lead_id}: {e}")


def sync_message_to_sheets(message_data):
    """Sincroniza uma mensagem com o Google Sheets"""
    if not sheets_service:
        return
    
    try:
        sheets_service.add_message(message_data)
        print(f"📊 Mensagem sincronizada com Sheets")
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar mensagem: {e}")


def update_sheets_metrics():
    """Atualiza métricas no Google Sheets"""
    if not sheets_service:
        return
    
    try:
        metrics = db.get_metrics_summary()
        sheets_service.update_metrics(metrics)
        print(f"📊 Métricas atualizadas no Sheets")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar métricas: {e}")


# =======================
# LOGIN / LOGOUT
# =======================
@app.route("/api/login", methods=["POST"])
@rate_limit('per_minute')
@validate_request('username', 'password')
@handle_errors
def login():
    data = request.json
    valid_user, username = validator.validate_username(data.get("username"))
    if not valid_user:
        return jsonify({"error": username}), 400

    valid_pass, password = validator.validate_password(data.get("password"))
    if not valid_pass:
        return jsonify({"error": password}), 400

    user = db.authenticate_user(username, password)
    if not user:
        audit_logger.log_action(0, "login_failed", "auth", 0, f"Username: {username}")
        return jsonify({"error": "Credenciais inválidas"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["name"] = user["name"]
    session["role"] = user["role"]

    audit_logger.log_action(user["id"], "login_success", "auth", user["id"], f"Login de {username}")
    return jsonify({"success": True, "user": user})


@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    user_id = session.get("user_id")
    audit_logger.log_action(user_id, "logout", "auth", user_id, "Logout")
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify({
        "id": session["user_id"],
        "username": session["username"],
        "name": session["name"],
        "role": session["role"]
    })

# =======================
# USUÁRIOS
# =======================
@app.route("/api/users", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@cached(ttl=60, key_prefix="users")  # ← ADICIONE ESTA LINHA
def get_users():
    return jsonify(db.get_all_users())


@app.route("/api/users", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin")
@validate_request('username', 'password', 'name', 'role')
@handle_errors
def create_user():
    data = request.json
    uid = db.create_user(data["username"], data["password"], data["name"], data["role"])
    if uid:
        audit_logger.log_action(session["user_id"], "user_created", "user", uid, f"Usuário {data['username']}")
        return jsonify({"success": True, "user_id": uid})
    return jsonify({"error": "Usuário já existe"}), 400


@app.route("/api/users/<int:user_id>", methods=["PUT"])
@rate_limit('per_minute')
@role_required("admin")
@handle_errors
def update_user(user_id):
    data = request.json
    db.update_user(user_id, data["name"], data["role"], data.get("active", 1))
    audit_logger.log_action(session["user_id"], "user_updated", "user", user_id, f"Usuário {user_id}")
    return jsonify({"success": True})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@rate_limit('per_minute')
@role_required("admin")
@handle_errors
def delete_user(user_id):
    db.delete_user(user_id)
    audit_logger.log_action(session["user_id"], "user_deleted", "user", user_id, f"Usuário {user_id}")
    return jsonify({"success": True})


@app.route("/api/users/<int:user_id>/password", methods=["PUT"])
@rate_limit('per_minute')
@role_required("admin")
@validate_request('new_password')
@handle_errors
def change_password(user_id):
    data = request.json
    db.change_user_password(user_id, data["new_password"])
    audit_logger.log_action(session["user_id"], "password_changed", "user", user_id, f"Senha alterada")
    return jsonify({"success": True})

# =======================
# LEADS
# =======================
@app.route("/api/leads", methods=["GET"])
@rate_limit('per_minute')
@login_required
@cached(ttl=30, key_prefix="leads")  # ← ADICIONE ESTA LINHA
def get_leads():
    role = session["role"]
    uid = session["user_id"]
    leads = db.get_all_leads() if role in ["admin", "gestor"] else db.get_leads_by_vendedor(uid)
    
    # Adiciona tags a cada lead
    for lead in leads:
        lead['tags'] = db.get_lead_tags(lead['id'])
    
    return jsonify(leads)


@app.route("/api/leads/queue", methods=["GET"])
@rate_limit('per_minute')
@login_required
def get_leads_queue():
    leads = db.get_leads_by_status("novo")
    return jsonify(leads)


@app.route("/api/leads/<int:lead_id>", methods=["GET"])
@rate_limit('per_minute')
@login_required
@handle_errors
def get_lead(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Lead não encontrado"}), 404
    
    lead['tags'] = db.get_lead_tags(lead_id)
    return jsonify(lead)


@app.route("/api/leads/<int:lead_id>/assign", methods=["POST"])
@rate_limit('per_minute')
@login_required
@handle_errors
def assign_lead(lead_id):
    uid = session["user_id"]
    uname = session["name"]
    
    db.assign_lead(lead_id, uid)
    db.add_lead_log(lead_id, "lead_atribuido", uname, f"Lead atribuído para {uname}")
    audit_logger.log_action(uid, "lead_assigned", "lead", lead_id, f"Lead atribuído")

     # 🔔 Notificar atribuição
    lead = db.get_lead(lead_id)
    notification_service.notify_lead_assigned(lead, uname, uid, room='gestores')
    
    
    # 📊 Sincronizar com Google Sheets
    sync_lead_to_sheets(lead_id)

    # 🗑️ Invalida cache (ADICIONE ESTA LINHA)
    invalidate_cache("leads")
    
    socketio.emit("lead_assigned", {"lead_id": lead_id, "vendedor_id": uid}, room="gestores")
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>/status", methods=["PUT"])
@rate_limit('per_minute')
@login_required
@validate_request('status')
@handle_errors
def update_lead_status(lead_id):
    data = request.json
    status = data["status"]
    uname = session["name"]
    
    # 🔹 Pegar status antigo ANTES de atualizar
    lead_atual = db.get_lead(lead_id)
    old_status = lead_atual.get('status', 'novo') if lead_atual else 'novo'
    
    # Atualizar status
    db.update_lead_status(lead_id, status)
    db.add_lead_log(lead_id, "status_alterado", uname, f"Status alterado para {status}")
    audit_logger.log_action(session["user_id"], "status_changed", "lead", lead_id, f"Status: {status}")
    
    # 🔔 Notificar mudança de status
    lead_atualizado = db.get_lead(lead_id)
    if lead_atualizado:
        notification_service.notify_status_changed(lead_atualizado, old_status, status, room='gestores')
    
    # 📊 Sincronizar com Google Sheets
    sync_lead_to_sheets(lead_id)
    
    # 📊 Atualizar métricas
    update_sheets_metrics()

    invalidate_cache("leads")
    invalidate_cache("metrics")
   
    socketio.emit("lead_status_changed", {"lead_id": lead_id, "status": status}, room="gestores")
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>/transfer", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@validate_request('vendedor_id')
@handle_errors
def transfer_lead(lead_id):
    data = request.json
    vendedor_id = data["vendedor_id"]
    uname = session["name"]
    
    db.transfer_lead(lead_id, vendedor_id)
    db.add_lead_log(lead_id, "lead_transferido", uname, f"Lead transferido")
    audit_logger.log_action(session["user_id"], "lead_transferred", "lead", lead_id, f"Para vendedor {vendedor_id}")
    
    # 📊 Sincronizar com Google Sheets
    sync_lead_to_sheets(lead_id)
    
    socketio.emit("lead_transferred", {"lead_id": lead_id, "vendedor_id": vendedor_id}, room="gestores")
    return jsonify({"success": True})

# =======================
# MENSAGENS
# =======================
@app.route("/api/leads/<int:lead_id>/messages", methods=["GET"])
@rate_limit('per_minute')
@login_required
@handle_errors
def get_messages(lead_id):
    messages = db.get_messages_by_lead(lead_id)
    return jsonify(messages)


@app.route("/api/leads/<int:lead_id>/messages", methods=["POST"])
@rate_limit('per_minute')
@login_required
@validate_request('content')
@handle_errors
def send_message(lead_id):
    data = request.json
    
    # Validar conteúdo
    valid, content = validator.validate_text(data.get("content"), max_length=4096, field_name="Mensagem")
    if not valid:
        return jsonify({"error": content}), 400
    
    # Sanitizar HTML
    content = validator.sanitize_html(content)
    
    uid = session["user_id"]
    uname = session["name"]

    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Lead não encontrado"}), 404

    success = whatsapp.send_message(lead["phone"], content, uid)
    if success:
        db.add_lead_log(lead_id, "mensagem_enviada", uname, content[:80])
        audit_logger.log_action(uid, "message_sent", "message", lead_id, f"Mensagem enviada para lead {lead_id}")
        
        # 📊 Sincronizar mensagem com Google Sheets
        sync_message_to_sheets({
            'id': db.get_connection().cursor().lastrowid,
            'lead_id': lead_id,
            'lead_nome': lead['name'],
            'is_from_me': True,
            'mensagem': content,
            'timestamp': datetime.now().isoformat(),
            'status': 'enviada'
        })
        
        # 📊 Atualizar lead no Sheets (última mensagem)
        sync_lead_to_sheets(lead_id)
    
    return jsonify({"success": success})

# =======================
# NOTAS INTERNAS
# =======================
@app.route("/api/leads/<int:lead_id>/notes", methods=["GET"])
@rate_limit('per_minute')
@login_required
def get_notes(lead_id):
    return jsonify(db.get_internal_notes(lead_id))


@app.route("/api/leads/<int:lead_id>/notes", methods=["POST"])
@rate_limit('per_minute')
@login_required
@validate_request('note')
@handle_errors
def add_note(lead_id):
    data = request.json
    
    # Validar nota
    valid, note = validator.validate_text(data.get("note"), max_length=2000, field_name="Nota")
    if not valid:
        return jsonify({"error": note}), 400
    
    note = validator.sanitize_html(note)
    
    uid = session["user_id"]
    uname = session["name"]

    db.add_internal_note(lead_id, uid, note)
    db.add_lead_log(lead_id, "nota_adicionada", uname, note[:80])
    
    audit_logger.log_action(uid, "note_added", "note", lead_id, "Nota interna adicionada")

    socketio.emit("new_note", {"lead_id": lead_id, "note": note, "user_name": uname}, room="gestores")
    return jsonify({"success": True})

# =======================
# TIMELINE DO LEAD
# =======================
@app.route('/api/lead/<int:lead_id>/logs', methods=['GET'])
@rate_limit('per_minute')
@login_required
@handle_errors
def get_lead_logs(lead_id):
    """Retorna histórico do lead"""
    logs = db.get_lead_logs(lead_id)
    return jsonify(logs)

# ========================================
# 📊 ENDPOINT DE MÉTRICAS AVANÇADAS (CORRIGIDO)
# ========================================

from datetime import datetime, timedelta
from collections import defaultdict

@app.route('/api/metrics', methods=['GET'])
@login_required
def get_metrics():
    """Retorna métricas avançadas do CRM"""
    period = request.args.get('period', 'month')
    vendedor_id = request.args.get('vendedor_id', None)

    now = datetime.now()
    if period == 'day':
        start_date = now - timedelta(days=1)
    elif period == 'week':
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)

    conn = db.get_connection()
    c = conn.cursor()

    # ========= 1. BASE =========
    where_base = "WHERE l.created_at >= ?"
    params = [start_date.strftime('%Y-%m-%d %H:%M:%S')]
    if vendedor_id:
        where_base += " AND l.assigned_to = ?"
        params.append(vendedor_id)

    # ========= 2. MÉTRICAS GERAIS =========
    c.execute(f'''
        SELECT 
            COUNT(*) as total_leads,
            SUM(CASE WHEN status = 'ganho' THEN 1 ELSE 0 END) as leads_ganhos,
            SUM(CASE WHEN status = 'novo' THEN 1 ELSE 0 END) as leads_novo,
            SUM(CASE WHEN status = 'em_atendimento' THEN 1 ELSE 0 END) as leads_atendimento,
            SUM(CASE WHEN status = 'qualificado' THEN 1 ELSE 0 END) as leads_qualificado,
            SUM(CASE WHEN status = 'perdido' THEN 1 ELSE 0 END) as leads_perdido
        FROM leads l
        {where_base}
    ''', params)
    metrics = dict(c.fetchone() or {})

    metrics.setdefault('total_leads', 0)
    metrics.setdefault('leads_ganhos', 0)

    metrics['taxa_conversao'] = (
        round((metrics['leads_ganhos'] / metrics['total_leads']) * 100, 1)
        if metrics['total_leads'] > 0 else 0
    )

    # ========= 3. TEMPO MÉDIO DE RESPOSTA =========
    query_tempo = f'''
        SELECT AVG(
            (julianday(m.timestamp) - julianday(l.created_at)) * 24 * 60
        ) as tempo_medio
        FROM messages m
        INNER JOIN leads l ON m.lead_id = l.id
        WHERE m.sender_type = 'vendedor'
        AND m.id = (
            SELECT MIN(id)
            FROM messages
            WHERE lead_id = l.id AND sender_type = 'vendedor'
        )
        AND l.created_at >= ?
    '''
    params_tempo = [start_date.strftime('%Y-%m-%d %H:%M:%S')]
    if vendedor_id:
        query_tempo += " AND l.assigned_to = ?"
        params_tempo.append(vendedor_id)

    c.execute(query_tempo, params_tempo)
    tempo = c.fetchone()
    metrics['tempo_resposta'] = round(tempo['tempo_medio'] or 0, 1)

    # ========= 4. SLA =========
    meta_sla = 15
    query_sla = f'''
        SELECT 
            COUNT(*) as total,
            SUM(CASE 
                WHEN (julianday(m.timestamp) - julianday(l.created_at)) * 24 * 60 <= {meta_sla}
                THEN 1 ELSE 0 
            END) as dentro_sla
        FROM messages m
        INNER JOIN leads l ON m.lead_id = l.id
        WHERE m.sender_type = 'vendedor'
        AND m.id = (
            SELECT MIN(id)
            FROM messages
            WHERE lead_id = l.id AND sender_type = 'vendedor'
        )
        AND l.created_at >= ?
    '''
    params_sla = [start_date.strftime('%Y-%m-%d %H:%M:%S')]
    if vendedor_id:
        query_sla += " AND l.assigned_to = ?"
        params_sla.append(vendedor_id)

    c.execute(query_sla, params_sla)
    sla = dict(c.fetchone() or {'total': 0, 'dentro_sla': 0})
    if sla['total'] > 0:
        sla['dentro_sla'] = round((sla['dentro_sla'] / sla['total']) * 100, 1)
        sla['fora_sla'] = round(100 - sla['dentro_sla'], 1)
    else:
        sla['dentro_sla'] = 0
        sla['fora_sla'] = 0
    sla['meta_minutos'] = meta_sla
    metrics['sla_compliance'] = sla

    # ========= 5. DISTRIBUIÇÃO DE CARGA =========
    c.execute(f'''
        SELECT 
            COALESCE(u.name, 'Sem atribuir') as vendedor,
            COUNT(*) as leads
        FROM leads l
        LEFT JOIN users u ON l.assigned_to = u.id
        {where_base}
        GROUP BY u.id, u.name
        ORDER BY leads DESC
    ''', params)
    carga = []
    for row in c.fetchall():
        total_leads = metrics['total_leads'] or 1
        carga.append({
            'vendedor': row['vendedor'],
            'leads': row['leads'],
            'percent': round((row['leads'] / total_leads) * 100, 1)
        })
    metrics['distribuicao_carga'] = carga

    # ========= 6. RANKING =========
    c.execute(f'''
        SELECT 
            u.name,
            COUNT(*) as total_leads,
            SUM(CASE WHEN l.status = 'ganho' THEN 1 ELSE 0 END) as ganhos,
            ROUND(
                (SUM(CASE WHEN l.status = 'ganho' THEN 1.0 ELSE 0 END) / COUNT(*)) * 100, 
                1
            ) as taxa
        FROM leads l
        INNER JOIN users u ON l.assigned_to = u.id
        {where_base}
        GROUP BY u.id, u.name
        ORDER BY ganhos DESC, taxa DESC
        LIMIT 5
    ''', params)
    ranking = []
    for row in c.fetchall():
        ranking.append({
            'name': row['name'],
            'ganhos': row['ganhos'],
            'taxa': row['taxa'] or 0
        })
    metrics['ranking'] = ranking

    # ========= 7. FUNIL =========
    metrics['funil'] = {
        'novo': metrics.get('leads_novo', 0),
        'em_atendimento': metrics.get('leads_atendimento', 0),
        'qualificado': metrics.get('leads_qualificado', 0),
        'ganho': metrics.get('leads_ganhos', 0),
        'perdido': metrics.get('leads_perdido', 0)
    }

    conn.close()
    return jsonify(metrics)


# =======================
# LOGS DE AUDITORIA
# =======================
@app.route("/api/audit-log", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def get_audit_log():
    """Retorna logs de auditoria"""
    limit = request.args.get('limit', 100, type=int)
    logs = db.get_audit_logs(limit)
    return jsonify(logs)

# =======================
# TAGS (Sistema de Tags)
# =======================
@app.route("/api/tags", methods=["GET"])
@rate_limit('per_minute')
@login_required
@cached(ttl=120, key_prefix="tags")  # ← ADICIONE ESTA LINHA
def get_all_tags():
    """Retorna todas as tags disponíveis"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM tags ORDER BY name")
        tags = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(tags)
    except:
        return jsonify([])


@app.route("/api/tags", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@validate_request('name', 'color')
@handle_errors
def create_tag():
    """Cria uma nova tag"""
    data = request.json
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (data["name"], data["color"]))
        conn.commit()
        tag_id = c.lastrowid
        conn.close()
        
        audit_logger.log_action(session["user_id"], "tag_created", "tag", tag_id, f"Tag {data['name']}")
        return jsonify({"success": True, "tag_id": tag_id})
    except:
        return jsonify({"error": "Erro ao criar tag"}), 500


@app.route("/api/leads/<int:lead_id>/tags", methods=["GET"])
@rate_limit('per_minute')
@login_required
def get_lead_tags_endpoint(lead_id):
    """Retorna tags de um lead"""
    tags = db.get_lead_tags(lead_id)
    return jsonify(tags)


@app.route("/api/leads/<int:lead_id>/tags", methods=["POST"])
@rate_limit('per_minute')
@login_required
@validate_request('tag_id')
@handle_errors
def add_tag_to_lead(lead_id):
    """Adiciona tag a um lead"""
    data = request.json
    tag_id = data["tag_id"]
    
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO lead_tags (lead_id, tag_id) VALUES (?, ?)", (lead_id, tag_id))
        conn.commit()
        conn.close()
        
        db.add_lead_log(lead_id, "tag_adicionada", session["name"], f"Tag ID {tag_id}")
        audit_logger.log_action(session["user_id"], "tag_added_to_lead", "lead", lead_id, f"Tag {tag_id}")
        
        # 📊 Sincronizar com Google Sheets
        sync_lead_to_sheets(lead_id)
        
        return jsonify({"success": True})
    except:
        return jsonify({"error": "Erro ao adicionar tag"}), 500


@app.route("/api/leads/<int:lead_id>/tags/<int:tag_id>", methods=["DELETE"])
@rate_limit('per_minute')
@login_required
@handle_errors
def remove_tag_from_lead(lead_id, tag_id):
    """Remove tag de um lead"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM lead_tags WHERE lead_id = ? AND tag_id = ?", (lead_id, tag_id))
        conn.commit()
        conn.close()
        
        db.add_lead_log(lead_id, "tag_removida", session["name"], f"Tag ID {tag_id}")
        audit_logger.log_action(session["user_id"], "tag_removed_from_lead", "lead", lead_id, f"Tag {tag_id}")
        
        # 📊 Sincronizar com Google Sheets
        sync_lead_to_sheets(lead_id)
        
        return jsonify({"success": True})
    except:
        return jsonify({"error": "Erro ao remover tag"}), 500

# =======================
# SLA (Sistema de SLA)
# =======================
@app.route("/api/leads/<int:lead_id>/sla", methods=["GET"])
@rate_limit('per_minute')
@login_required
def get_lead_sla(lead_id):
    """Retorna informações de SLA do lead"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM sla_tracking WHERE lead_id = ?", (lead_id,))
        sla = c.fetchone()
        conn.close()
        return jsonify(dict(sla) if sla else {})
    except:
        return jsonify({})


@app.route("/api/sla/metrics", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
def get_sla_metrics():
    """Retorna métricas de SLA"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(first_response_time) as avg_first_response,
                AVG(resolution_time) as avg_resolution
            FROM sla_tracking
            WHERE first_response_time IS NOT NULL
        """)
        metrics = dict(c.fetchone())
        conn.close()
        return jsonify(metrics)
    except:
        return jsonify({})


@app.route("/api/sla/alerts", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
def get_sla_alerts():
    """Retorna alertas de SLA próximos do limite"""
    threshold = request.args.get('threshold', 5, type=int)
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT l.*, s.* 
            FROM leads l
            INNER JOIN sla_tracking s ON l.id = s.lead_id
            WHERE s.first_response_time IS NULL 
            AND (julianday('now') - julianday(l.created_at)) * 24 * 60 > ?
            ORDER BY l.created_at ASC
        """, (threshold,))
        alerts = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(alerts)
    except:
        return jsonify([])

# =======================
# WEBHOOK DO WHATSAPP - ✅ COM SINCRONIZAÇÃO SHEETS
# =======================
@app.route("/api/webhook/message", methods=["POST"])
@rate_limit('per_hour')
@handle_errors
def webhook_message():
    data = request.get_json(force=True)
    print(f"📩 Webhook recebido: {data}")

    try:
        # ✅ Suporta tanto formato Baileys (from/body) quanto Venom (phone/content)
        phone_raw = data.get("from") or data.get("phone", "")
        content = data.get("body") or data.get("content", "")
        name = data.get("notifyName") or data.get("name", "Lead")
        
        # Limpa telefone
        phone = str(phone_raw).strip().replace("+", "").replace(" ", "").replace("-", "").replace("@c.us", "").replace("@s.whatsapp.net", "")
        content = str(content).strip()
        name = str(name).strip()
        timestamp = datetime.now().isoformat()

        print(f"📞 Telefone limpo: {phone}")
        print(f"💬 Conteúdo: {content[:50]}...")
        print(f"👤 Nome: {name}")

        if not phone.isdigit():
            print(f"⚠️ Telefone inválido recebido: {phone_raw} -> {phone}")
            return jsonify({"error": "Telefone inválido"}), 400

        if not content:
            print("⚠️ Webhook ignorado (sem conteúdo).")
            return jsonify({"error": "Sem conteúdo"}), 400

        # 🔹 Cria ou busca o lead
        lead = db.create_or_get_lead(phone, name)
        
        if not lead:
            print(f"❌ Erro ao criar/buscar lead para {phone}")
            return jsonify({"error": "Erro ao processar lead"}), 500
        
        # 🔔 Notificar novo lead
        notification_service.notify_new_lead(lead, room='gestores')

        # 📊 Sincronizar lead com Google Sheets
        sync_lead_to_sheets(lead["id"])

        # 🔹 Registra mensagem
        db.add_message(lead["id"], "lead", name, content)

        # 🔔 Notificar nova mensagem
        notification_service.notify_new_message(lead, content, room='gestores')
        
        # 📊 Sincronizar mensagem com Google Sheets
        sync_message_to_sheets({
            'id': db.get_connection().cursor().lastrowid,
            'lead_id': lead["id"],
            'lead_nome': name,
            'is_from_me': False,
            'mensagem': content,
            'timestamp': timestamp,
            'status': 'recebida'
        })

        # 🔹 Log de histórico
        db.add_lead_log(lead["id"], "mensagem_recebida", name, content[:100])

        # 🤖 RESPOSTA AUTOMÁTICA DA IA
        if ia_assistant:
            try:
                resposta_ia = ia_assistant.processar_mensagem(lead["id"], content)

                if resposta_ia:
                    # Enviar resposta via WhatsApp
                    success = whatsapp.send_message(phone, resposta_ia, user_id=0)  # user_id=0 = IA

                    if success:
                        # Registrar mensagem da IA no banco
                        db.add_message(lead["id"], "ia", "Assistente Virtual", resposta_ia)
                        db.increment_ia_message_count(lead["id"])

                        # Log da ação
                        db.add_lead_log(lead["id"], "ia_resposta", "IA Assistant", resposta_ia[:100])

                        # Notificar via Socket.io
                        socketio.emit("new_message", {
                            "lead_id": lead["id"],
                            "phone": phone,
                            "name": "Assistente Virtual",
                            "content": resposta_ia,
                            "timestamp": datetime.now().isoformat(),
                            "sender_type": "ia"
                        }, room="gestores")

                        print(f"🤖 IA respondeu ao lead {lead['id']}")
            except Exception as e_ia:
                print(f"⚠️ Erro na IA (não bloqueante): {e_ia}")

        # 🔹 Emite atualização em tempo real
        socketio.emit("new_message", {
            "lead_id": lead["id"],
            "phone": phone,
            "name": name,
            "content": content,
            "timestamp": timestamp,
            "sender_type": "lead"
        }, room="gestores")

        print(f"✅ Mensagem processada com sucesso!")
        print(f"   Lead ID: {lead['id']}")
        print(f"   Nome: {name}")
        print(f"   Telefone: {phone}")
        print(f"   📊 Sincronizado com Google Sheets")
        print("")
        
        return jsonify({"success": True, "lead_id": lead["id"]}), 200
    
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =======================
# SIMULADOR (Modo Desenvolvimento)
# =======================
@app.route("/api/simulate/message", methods=["POST"])
@rate_limit('per_minute')
@handle_errors
def simulate_message():
    """Simula recebimento de mensagem (para testes sem WhatsApp real)"""
    data = request.json
    
    # Simula o formato do VenomBot
    simulated_data = {
        "from": data.get("phone", "") + "@c.us",
        "body": data.get("content", ""),
        "notifyName": data.get("name", "Lead Teste"),
        "timestamp": int(datetime.now().timestamp()),
        "fromMe": False
    }
    
    # Chama o webhook internamente
    return webhook_message()

# =======================
# WHATSAPP STATUS
# =======================
@app.route("/api/whatsapp/status", methods=["GET"])
@login_required
def whatsapp_status():
    return jsonify(whatsapp.get_status())

# =======================
# SOCKET.IO EVENTS
# =======================
@socketio.on("connect")
def on_connect():
    print("🔌 Cliente conectado")

@socketio.on("disconnect")
def on_disconnect():
    print("🔌 Cliente desconectado")

@socketio.on("join_room")
def on_join(data):
    room = data.get("room")
    join_room(room)
    print(f"📍 Entrou na sala: {room}")

@socketio.on("leave_room")
def on_leave(data):
    room = data.get("room")
    leave_room(room)
    print(f"📍 Saiu da sala: {room}")

# =======================
# HEALTH CHECK
# =======================
@app.route("/health", methods=["GET"])
def health_check():
    """Health check para monitoramento"""
    whatsapp_status = whatsapp.ensure_connected()
    sheets_status = sheets_service is not None
    
    return jsonify({
        "status": "healthy" if (whatsapp_status and sheets_status) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "ok",
            "whatsapp": "connected" if whatsapp_status else "disconnected",
            "google_sheets": "connected" if sheets_status else "disconnected"
        }
    })

# =======================
# CACHE STATS
# =======================
@app.route("/api/cache/stats", methods=["GET"])
@role_required("admin")
def cache_stats_endpoint():
    """Retorna estatísticas do cache"""
    return jsonify(get_cache_stats())

# =======================
# SISTEMA DE ALERTAS
# =======================

@app.route("/api/alerts", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def get_alerts():
    """Retorna alertas ativos"""
    vendedor_id = request.args.get('vendedor_id', type=int)
    
    alert_system = AlertSystem(db)
    alerts = alert_system.get_active_alerts(vendedor_id)
    
    return jsonify({
        "alerts": alerts,
        "stats": alert_system.get_alert_stats()
    })


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def resolve_alert(alert_id):
    """Marca alerta como resolvido"""
    alert_system = AlertSystem(db)
    alert_system.resolve_alert(alert_id)
    
    audit_logger.log_action(
        session["user_id"], 
        "alert_resolved", 
        "alert", 
        alert_id, 
        "Alerta resolvido"
    )
    
    return jsonify({"success": True})


@app.route("/api/alerts/dashboard", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def get_alerts_dashboard():
    """Retorna dados do dashboard de alertas"""
    dashboard_data = alert_monitoring.get_dashboard_data()
    return jsonify(dashboard_data)


@app.route("/api/alerts/check-now", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin")
@handle_errors
def check_alerts_now():
    """Força verificação de alertas (apenas admin)"""
    new_alerts = check_alerts_once(db, socketio, notification_service, whatsapp)  # ← ADICIONE whatsapp
    
    return jsonify({
        "success": True,
        "alerts_found": len(new_alerts),
        "alerts": new_alerts
    })

# =======================
# CONFIGURAÇÃO WHATSAPP GESTORES
# =======================

@app.route("/api/gestores/whatsapp-config", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def get_gestor_whatsapp_config():
    """Retorna configuração de WhatsApp do gestor"""
    user_id = session["user_id"]
    
    notifier = GestorWhatsAppNotifier(db, whatsapp)
    config = notifier.get_config(user_id)
    
    return jsonify(config if config else {})


@app.route("/api/gestores/whatsapp-config", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@validate_request('phone')
@handle_errors
def set_gestor_whatsapp_config():
    """Configura WhatsApp para receber alertas"""
    data = request.json
    user_id = session["user_id"]
    
    # Validar telefone
    phone = data.get("phone", "").strip()
    if not phone.isdigit() or len(phone) < 10:
        return jsonify({"error": "Telefone inválido"}), 400
    
    notifier = GestorWhatsAppNotifier(db, whatsapp)
    
    config_id = notifier.add_gestor_config(
        user_id=user_id,
        phone=phone,
        receive_critical=data.get("receive_critical", True),
        receive_danger=data.get("receive_danger", True),
        receive_warning=data.get("receive_warning", False)
    )
    
    audit_logger.log_action(
        user_id, 
        "whatsapp_config_updated", 
        "config", 
        config_id, 
        f"WhatsApp configurado: {phone}"
    )
    
    return jsonify({
        "success": True,
        "config_id": config_id,
        "message": "Configuração salva com sucesso!"
    })


@app.route("/api/gestores/whatsapp-config/test", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def test_gestor_whatsapp():
    """Envia mensagem de teste para o gestor"""
    user_id = session["user_id"]
    
    notifier = GestorWhatsAppNotifier(db, whatsapp)
    success = notifier.test_notification(user_id)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Mensagem de teste enviada com sucesso!"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Falha ao enviar mensagem de teste"
        }), 500


@app.route("/api/gestores/whatsapp-config", methods=["DELETE"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def disable_gestor_whatsapp():
    """Desativa notificações WhatsApp"""
    user_id = session["user_id"]
    
    notifier = GestorWhatsAppNotifier(db, whatsapp)
    notifier.disable_config(user_id)
    
    audit_logger.log_action(
        user_id, 
        "whatsapp_config_disabled", 
        "config", 
        user_id, 
        "Notificações WhatsApp desativadas"
    )
    
    return jsonify({
        "success": True,
        "message": "Notificações desativadas"
    })

# =======================
# 🤖 IA ASSISTANT - ENDPOINTS
# =======================

@app.route("/api/ia/status", methods=["GET"])
@login_required
@handle_errors
def get_ia_status():
    """Retorna status e configuração da IA"""
    if not ia_assistant:
        return jsonify({
            "habilitada": False,
            "motivo": "IA não inicializada"
        })

    stats = ia_assistant.get_estatisticas()
    db_stats = db.get_estatisticas_ia()

    return jsonify({
        "habilitada": True,
        "configuracao": stats,
        "estatisticas": db_stats
    })


@app.route("/api/ia/leads-qualificados", methods=["GET"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def get_leads_qualificados_ia():
    """Retorna leads qualificados pela IA (prontos para atribuição)"""
    leads = db.get_leads_qualificados_ia()

    # Adicionar respostas de qualificação para cada lead
    for lead in leads:
        lead['qualificacao'] = db.get_lead_qualificacao_respostas(lead['id'])

    return jsonify(leads)


@app.route("/api/leads/<int:lead_id>/qualificacao", methods=["GET"])
@rate_limit('per_minute')
@login_required
@handle_errors
def get_lead_qualificacao(lead_id):
    """Retorna respostas de qualificação de um lead específico"""
    respostas = db.get_lead_qualificacao_respostas(lead_id)

    return jsonify({
        "lead_id": lead_id,
        "respostas": respostas,
        "total": len(respostas)
    })


@app.route("/api/ia/forcar-escalacao/<int:lead_id>", methods=["POST"])
@rate_limit('per_minute')
@role_required("admin", "gestor")
@handle_errors
def forcar_escalacao_humano(lead_id):
    """Força escalação de lead para atendimento humano"""
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Lead não encontrado"}), 404

    # Marcar como escalado
    db.marcar_lead_escalado_humano(lead_id)
    db.update_lead_status(lead_id, "novo")
    db.add_lead_log(
        lead_id,
        "ia_escalado_manual",
        session.get("name", "Sistema"),
        "Escalado manualmente por gestor"
    )

    audit_logger.log_action(
        session["user_id"],
        "ia_escalacao_manual",
        "lead",
        lead_id,
        "Lead escalado manualmente"
    )

    return jsonify({
        "success": True,
        "message": "Lead escalado para atendimento humano"
    })

# =======================
# INICIALIZAÇÃO
# =======================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 CRM WhatsApp - Versão Otimizada + Google Sheets")
    print("=" * 60)
    print("✅ Rate Limiting ativado")
    print("✅ Validações de input implementadas")
    print("✅ Retry logic no WhatsApp")
    print("✅ Paginação e busca otimizadas")
    print("✅ Logs de auditoria ativos")
    print("✅ Cache de performance configurado")
    print("✅ Webhook CORRIGIDO para VenomBot")
    print("✅ Google Sheets - Sincronização em tempo real")
    print("=" * 60)
    print("🌐 API: http://localhost:5000")
    print("🔌 Socket.io ativo")
    print("📊 Health check: http://localhost:5000/health")
    print("📡 Webhook: http://localhost:5000/api/webhook/message")
    if sheets_service:
        print(f"📊 Google Sheets: {sheets_service.get_spreadsheet_url()}")
    print("=" * 60)

    socketio.run(app, debug=False, host="0.0.0.0", port=5000)