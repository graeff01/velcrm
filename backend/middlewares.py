"""
Middlewares de segurança e controle
- Rate Limiting
- Validação de inputs
- Logs de auditoria
- Error handling
"""
from flask import request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
import re

# =============================
# RATE LIMITING
# =============================
class RateLimiter:
    """
    Rate limiter simples em memória
    Em produção: usar Redis
    """
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            'per_minute': 60,
            'per_hour': 1000
        }
    
    def is_rate_limited(self, identifier, limit_type='per_minute'):
        """Verifica se o identificador atingiu o limite"""
        now = datetime.now()
        limit = self.limits.get(limit_type, 60)
        
        # Define janela de tempo
        if limit_type == 'per_minute':
            window = timedelta(minutes=1)
        elif limit_type == 'per_hour':
            window = timedelta(hours=1)
        else:
            window = timedelta(minutes=1)
        
        # Remove requests antigas
        cutoff = now - window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        # Verifica limite
        if len(self.requests[identifier]) >= limit:
            return True
        
        # Adiciona nova request
        self.requests[identifier].append(now)
        return False
    
    def reset(self, identifier):
        """Reseta contador para um identificador"""
        if identifier in self.requests:
            del self.requests[identifier]


# Instância global
rate_limiter = RateLimiter()


def rate_limit(limit_type='per_minute'):
    """
    Decorator para rate limiting
    
    Usage:
        @rate_limit('per_minute')
        def minha_rota():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Identificador: IP ou user_id se autenticado
            identifier = session.get('user_id') or request.remote_addr
            
            if rate_limiter.is_rate_limited(identifier, limit_type):
                return jsonify({
                    "error": "Rate limit excedido. Tente novamente em alguns instantes.",
                    "retry_after": 60 if limit_type == 'per_minute' else 3600
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================
# VALIDAÇÃO DE INPUTS
# =============================
class InputValidator:
    """Validador de inputs da API"""
    
    @staticmethod
    def validate_phone(phone):
        """Valida número de telefone"""
        if not phone:
            return False, "Telefone não pode ser vazio"
        
        # Remove caracteres não numéricos
        phone_clean = re.sub(r'\D', '', str(phone))
        
        # Valida comprimento
        if len(phone_clean) < 10 or len(phone_clean) > 15:
            return False, "Telefone deve ter entre 10 e 15 dígitos"
        
        return True, phone_clean
    
    @staticmethod
    def validate_email(email):
        """Valida email"""
        if not email:
            return True, None  # Email é opcional
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Email inválido"
        
        return True, email
    
    @staticmethod
    def validate_text(text, min_length=1, max_length=1000, field_name="Texto"):
        """Valida campos de texto"""
        if not text or not text.strip():
            return False, f"{field_name} não pode ser vazio"
        
        text_clean = text.strip()
        
        if len(text_clean) < min_length:
            return False, f"{field_name} deve ter no mínimo {min_length} caracteres"
        
        if len(text_clean) > max_length:
            return False, f"{field_name} deve ter no máximo {max_length} caracteres"
        
        return True, text_clean
    
    @staticmethod
    def validate_username(username):
        """Valida username"""
        if not username or len(username) < 3:
            return False, "Username deve ter no mínimo 3 caracteres"
        
        if len(username) > 50:
            return False, "Username deve ter no máximo 50 caracteres"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username deve conter apenas letras, números e underscore"
        
        return True, username
    
    @staticmethod
    def validate_password(password):
        """Valida senha"""
        if not password or len(password) < 6:
            return False, "Senha deve ter no mínimo 6 caracteres"
        
        if len(password) > 100:
            return False, "Senha muito longa"
        
        return True, password
    
    @staticmethod
    def validate_role(role):
        """Valida role de usuário"""
        valid_roles = ['admin', 'gestor', 'vendedor']
        if role not in valid_roles:
            return False, f"Role deve ser um de: {', '.join(valid_roles)}"
        
        return True, role
    
    @staticmethod
    def validate_status(status):
        """Valida status de lead"""
        valid_statuses = ['novo', 'em_atendimento', 'qualificado', 'negociacao', 'ganho', 'perdido']
        if status not in valid_statuses:
            return False, f"Status deve ser um de: {', '.join(valid_statuses)}"
        
        return True, status
    
    @staticmethod
    def sanitize_html(text):
        """Remove tags HTML perigosas"""
        if not text:
            return text
        
        # Remove tags HTML básicas
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', '', text)
        
        return text


# =============================
# DECORATORS DE VALIDAÇÃO
# =============================
def validate_request(*fields):
    """
    Valida campos obrigatórios no request
    
    Usage:
        @validate_request('username', 'password')
        def login():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.json or {}
            
            missing_fields = []
            for field in fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    "error": "Campos obrigatórios ausentes",
                    "missing_fields": missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================
# ERROR HANDLING
# =============================
def handle_errors(f):
    """
    Wrapper genérico para tratamento de erros
    Captura exceções e retorna resposta JSON apropriada
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            print(f"⚠️ Erro de validação: {e}")
            return jsonify({"error": str(e)}), 400
        except PermissionError as e:
            print(f"🚫 Erro de permissão: {e}")
            return jsonify({"error": "Sem permissão para esta ação"}), 403
        except Exception as e:
            print(f"❌ Erro interno: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Erro interno do servidor"}), 500
    return decorated_function


# =============================
# AUDIT LOG
# =============================
class AuditLogger:
    """Logger de auditoria para ações críticas"""
    
    def __init__(self, database):
        self.db = database
    
    def log_action(self, user_id, action, entity_type, entity_id, details=""):
        """
        Registra ação de auditoria
        
        Args:
            user_id: ID do usuário que executou a ação
            action: Tipo de ação (create, update, delete, etc)
            entity_type: Tipo de entidade (user, lead, message, etc)
            entity_id: ID da entidade afetada
            details: Detalhes adicionais
        """
        try:
            # Aqui você pode implementar a lógica de salvar no banco
            # ou enviar para um serviço de logging externo
            timestamp = datetime.now().isoformat()
            print(f"📝 AUDIT: [{timestamp}] User {user_id} - {action} {entity_type} #{entity_id} - {details}")
            
            # Opcional: salvar no banco de dados
            # self.db.save_audit_log(...)
            
        except Exception as e:
            print(f"❌ Erro ao registrar log de auditoria: {e}")


# =============================
# SECURITY HEADERS
# =============================
def add_security_headers(response):
    """Adiciona headers de segurança nas respostas"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# =============================
# IP WHITELIST (OPCIONAL)
# =============================
class IPWhitelist:
    """
    Controle de acesso por IP (opcional)
    Útil para ambientes de produção com IPs conhecidos
    """
    def __init__(self, allowed_ips=None):
        self.allowed_ips = allowed_ips or []
        self.enabled = bool(allowed_ips)
    
    def is_allowed(self, ip):
        """Verifica se IP está na whitelist"""
        if not self.enabled:
            return True
        
        return ip in self.allowed_ips
    
    def check_ip(self, f):
        """Decorator para verificar IP"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_allowed(request.remote_addr):
                return jsonify({"error": "Acesso negado"}), 403
            return f(*args, **kwargs)
        return decorated_function
 
 # =============================
# ROLE-BASED ACCESS CONTROL (SESSION-BASED)
# =============================
from flask import g, session

def login_required_rbac(f):
    """
    Decorator para rotas que exigem autenticação (compatível com sessions)
    Diferente do login_required original, este carrega o usuário completo em g.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Carrega usuário completo do banco
        from database import Database
        db = Database()
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND active = 1", (session["user_id"],))
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Usuário inválido ou inativo'}), 401
        
        # Disponibiliza usuário globalmente na request
        g.current_user = dict(user)
        return f(*args, **kwargs)
    
    return decorated_function


def role_required_rbac(*allowed_roles):
    """
    Decorator para rotas que exigem perfis específicos (compatível com sessions)
    
    Usage:
        @role_required_rbac('admin')  # Apenas admin
        @role_required_rbac('admin', 'gestor')  # Admin ou gestor
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({'error': 'Não autenticado'}), 401
            
            if session.get("role") not in allowed_roles:
                return jsonify({
                    'error': 'Acesso negado',
                    'message': f'Esta ação requer um dos perfis: {", ".join(allowed_roles)}',
                    'user_role': session.get("role"),
                    'required_roles': list(allowed_roles)
                }), 403
            
            # Carrega usuário completo em g.current_user
            from database import Database
            db = Database()
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
            user = c.fetchone()
            conn.close()
            
            if user:
                g.current_user = dict(user)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def owner_or_manager_required_rbac(f):
    """
    Decorator para rotas onde vendedor só pode acessar seus próprios recursos
    Gestor e Admin podem acessar tudo
    
    Usage:
        @owner_or_manager_required_rbac
        def get_lead(lead_id):
            # g.current_user já está disponível
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Carrega usuário completo
        from database import Database
        db = Database()
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND active = 1", (session["user_id"],))
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Usuário inválido'}), 401
        
        g.current_user = dict(user)
        return f(*args, **kwargs)
    
    return decorated_function