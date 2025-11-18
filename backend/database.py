import sqlite3
import bcrypt
import hashlib  # Manter temporariamente para migração de hashes antigos

class Database:
    def __init__(self, db_name="../crm.db"):

        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # ← permite acessar colunas por nome
        return conn

    # =======================
    # INICIALIZAÇÃO
    # =======================
    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()

        # Usuários
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                name TEXT,
                role TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        # Leads (com campos da IA v2.0)
        c.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                status TEXT DEFAULT 'novo',
                assigned_to INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Campos de qualificação IA
                ai_qualified INTEGER DEFAULT 0,
                qualification_score INTEGER DEFAULT 0,
                classification TEXT DEFAULT 'new',
                prioridade TEXT DEFAULT 'normal',
                sentimento TEXT DEFAULT 'neutro',
                
                -- Campos de respostas coletadas
                interesse TEXT,
                orcamento TEXT,
                prazo TEXT,
                preferencia_contato TEXT,
                tipo_cliente TEXT,
                tamanho_empresa TEXT,
                
                -- Controle de fluxo da IA
                proxima_pergunta_id TEXT
            )
        """)

        # Mensagens
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                sender_type TEXT,
                sender_name TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Notas internas
        c.execute("""
            CREATE TABLE IF NOT EXISTS internal_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                user_id INTEGER,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Logs de auditoria
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                entity_type TEXT,
                entity_id INTEGER,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Timeline do lead
        c.execute("""
            CREATE TABLE IF NOT EXISTS lead_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                user_name TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)

        # ✨ NOVA TABELA: Respostas da qualificação da IA
        c.execute("""
            CREATE TABLE IF NOT EXISTS lead_qualificacao_respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                pergunta_id TEXT NOT NULL,
                resposta TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
            )
        """)

        # Índices para performance
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_qualificacao_lead_id 
            ON lead_qualificacao_respostas(lead_id)
        """)
        
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_classification 
            ON leads(classification)
        """)
        
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_ai_qualified 
            ON leads(ai_qualified)
        """)

        conn.commit()

        # Usuário admin padrão
        c.execute("SELECT * FROM users WHERE username = 'admin'")
        if not c.fetchone():
            self.create_user("admin", "admin123", "Administrador", "admin")
            print("👤 Usuário criado: admin / admin123")

        conn.close()

    # =======================
    # USUÁRIOS
    # =======================
    def hash_password(self, password):
        """Hash de senha usando bcrypt (seguro contra força bruta)"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _is_sha256_hash(self, hash_string):
        """Detecta se é um hash SHA256 antigo (64 caracteres hexadecimais)"""
        return len(hash_string) == 64 and all(c in '0123456789abcdef' for c in hash_string)

    def _sha256_hash(self, password):
        """Hash SHA256 (DEPRECATED - apenas para migração de senhas antigas)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, username, password):
        """Autentica usuário com suporte a migração de hashes SHA256 → bcrypt"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,))
        user = c.fetchone()

        if not user:
            conn.close()
            return None

        stored_hash = user["password"]

        # Verificar se é hash SHA256 antigo
        if self._is_sha256_hash(stored_hash):
            # Comparar com SHA256
            if stored_hash == self._sha256_hash(password):
                # ✅ Senha correta! Migrar para bcrypt automaticamente
                user_id = user["id"]
                new_hash = self.hash_password(password)
                c.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
                conn.commit()
                print(f"🔄 Senha do usuário '{username}' migrada de SHA256 → bcrypt")
                conn.close()
                return dict(user)
            else:
                conn.close()
                return None

        # Hash bcrypt (novo sistema)
        else:
            conn.close()
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                return dict(user)
            return None

    def create_user(self, username, password, name, role):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (username, password, name, role)
                VALUES (?, ?, ?, ?)
            """, (username, self.hash_password(password), name, role))
            conn.commit()
            uid = c.lastrowid
            conn.close()
            return uid
        except sqlite3.IntegrityError:
            return None

    def get_all_users(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, username, name, role, active FROM users")
        users = [dict(r) for r in c.fetchall()]
        conn.close()
        return users

    def update_user(self, user_id, name, role, active):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET name = ?, role = ?, active = ? WHERE id = ?", (name, role, active, user_id))
        conn.commit()
        conn.close()

    def delete_user(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    def change_user_password(self, user_id, new_password):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET password = ? WHERE id = ?", (self.hash_password(new_password), user_id))
        conn.commit()
        conn.close()

    # =======================
    # LEADS
    # =======================
    def create_or_get_lead(self, phone, name="Lead Desconhecido"):
        """Cria lead se não existir, ou retorna existente"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            phone = str(phone).replace("+", "").replace(" ", "").replace("-", "").replace("@c.us", "")

            # Verifica se já existe
            c.execute("SELECT * FROM leads WHERE phone = ?", (phone,))
            lead = c.fetchone()
            if lead:
                print(f"ℹ️ Lead existente encontrado: {lead['name']} ({phone})")
                conn.close()
                return dict(lead)

            # Cria novo lead
            c.execute("""
                INSERT INTO leads (name, phone, status, created_at)
                VALUES (?, ?, 'novo', datetime('now'))
            """, (name, phone))
            conn.commit()

            c.execute("SELECT * FROM leads WHERE phone = ?", (phone,))
            new_lead = c.fetchone()
            conn.close()
            print(f"🆕 Lead criado: {name} ({phone})")
            return dict(new_lead)

        except Exception as e:
            print(f"❌ Erro ao criar/obter lead: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_lead(self, lead_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        r = c.fetchone()
        conn.close()
        return dict(r) if r else None

    def get_lead_by_phone(self, phone):
        """Busca lead por número de telefone"""
        try:
            # Normaliza o telefone
            phone_clean = str(phone).replace("+", "").replace(" ", "").replace("-", "").replace("@c.us", "")
            
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM leads WHERE phone = ?", (phone_clean,))
            lead = c.fetchone()
            conn.close()
            
            if lead:
                return dict(lead)
            return None
            
        except Exception as e:
            print(f"❌ Erro ao buscar lead por telefone: {e}")
            return None

    def get_all_leads(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT l.*, u.name AS vendedor_name
            FROM leads l LEFT JOIN users u ON l.assigned_to = u.id
            ORDER BY l.updated_at DESC
        """)
        leads = [dict(r) for r in c.fetchall()]
        conn.close()
        return leads

    def get_leads_by_vendedor(self, user_id):
        """Retorna leads atribuídos a um vendedor específico"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT l.*, u.name AS vendedor_name
            FROM leads l LEFT JOIN users u ON l.assigned_to = u.id
            WHERE l.assigned_to = ?
            ORDER BY l.updated_at DESC
        """, (user_id,))
        leads = [dict(r) for r in c.fetchall()]
        conn.close()
        return leads

    def get_leads_by_status(self, status):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM leads WHERE status = ? ORDER BY updated_at DESC", (status,))
        leads = [dict(r) for r in c.fetchall()]
        conn.close()
        return leads

    def assign_lead(self, lead_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE leads
            SET assigned_to = ?, status = 'em_atendimento', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id, lead_id))
        conn.commit()
        conn.close()

    def update_lead_status(self, lead_id, status):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, lead_id))
        conn.commit()
        conn.close()

    def transfer_lead(self, lead_id, new_user_id):
        """Transfere lead para outro vendedor"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE leads
            SET assigned_to = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_user_id, lead_id))
        conn.commit()
        conn.close()

    # =======================
    # MENSAGENS / LOGS / NOTAS
    # =======================
    def add_message(self, lead_id, sender_type, sender_name, content):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO messages (lead_id, sender_type, sender_name, content)
            VALUES (?, ?, ?, ?)
        """, (lead_id, sender_type, sender_name, content))
        conn.commit()
        conn.close()

    def get_messages_by_lead(self, lead_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM messages WHERE lead_id = ? ORDER BY id ASC", (lead_id,))
        msgs = [dict(r) for r in c.fetchall()]
        conn.close()
        return msgs

    def add_internal_note(self, lead_id, user_id, note):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO internal_notes (lead_id, user_id, note) VALUES (?, ?, ?)", (lead_id, user_id, note))
        conn.commit()
        conn.close()

    def get_internal_notes(self, lead_id):
        """Retorna notas internas de um lead"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT n.*, u.name as user_name
            FROM internal_notes n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.lead_id = ?
            ORDER BY n.created_at DESC
        """, (lead_id,))
        notes = [dict(r) for r in c.fetchall()]
        conn.close()
        return notes

    def add_lead_log(self, lead_id, action, user_name, details=""):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO lead_logs (lead_id, action, user_name, details)
            VALUES (?, ?, ?, ?)
        """, (lead_id, action, user_name, details))
        conn.commit()
        conn.close()

    def get_lead_logs(self, lead_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM lead_logs WHERE lead_id = ? ORDER BY id DESC", (lead_id,))
        logs = [dict(r) for r in c.fetchall()]
        conn.close()
        return logs

    # =======================
    # LOGS DE AUDITORIA
    # =======================
    def add_audit_log(self, user_id, action, entity_type, entity_id, details=""):
        """Adiciona log de auditoria para rastreamento de ações"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action, entity_type, entity_id, details))
        conn.commit()
        conn.close()

    def get_audit_logs(self, limit=100):
        """Retorna logs de auditoria"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT a.*, u.name as user_name
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT ?
        """, (limit,))
        logs = [dict(r) for r in c.fetchall()]
        conn.close()
        return logs

    # =======================
    # TAGS (para extensão)
    # =======================
    def get_lead_tags(self, lead_id):
        """Retorna tags de um lead (se tabela existir)"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT t.* FROM tags t
                INNER JOIN lead_tags lt ON t.id = lt.tag_id
                WHERE lt.lead_id = ?
            """, (lead_id,))
            tags = [dict(r) for r in c.fetchall()]
            conn.close()
            return tags
        except sqlite3.OperationalError:
            # Tabela de tags ainda não existe
            return []

    # =======================
    # ✨ MÉTODOS DA IA v2.0
    # =======================
    
    def get_lead_qualificacao_respostas(self, lead_id):
        """
        Retorna todas as respostas da qualificação de um lead
        
        Returns:
            List[Dict]: Lista de dicionários com pergunta_id e resposta
        """
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM lead_qualificacao_respostas 
            WHERE lead_id = ? 
            ORDER BY created_at ASC
        """, (lead_id,))
        respostas = [dict(r) for r in c.fetchall()]
        conn.close()
        return respostas
    
    def add_lead_qualificacao_resposta(self, lead_id, pergunta_id, resposta):
        """
        Adiciona uma resposta da qualificação
        
        Args:
            lead_id: ID do lead
            pergunta_id: ID da pergunta (ex: 'nome', 'interesse', etc)
            resposta: Texto da resposta
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verificar se já existe resposta para essa pergunta
        c.execute("""
            SELECT id FROM lead_qualificacao_respostas 
            WHERE lead_id = ? AND pergunta_id = ?
        """, (lead_id, pergunta_id))
        
        existing = c.fetchone()
        
        if existing:
            # Atualizar resposta existente
            c.execute("""
                UPDATE lead_qualificacao_respostas 
                SET resposta = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (resposta, existing['id']))
        else:
            # Inserir nova resposta
            c.execute("""
                INSERT INTO lead_qualificacao_respostas (lead_id, pergunta_id, resposta)
                VALUES (?, ?, ?)
            """, (lead_id, pergunta_id, resposta))
        
        conn.commit()
        conn.close()
    
    def set_lead_proxima_pergunta(self, lead_id, pergunta_id):
        """
        Define qual é a próxima pergunta que a IA deve fazer
        
        Args:
            lead_id: ID do lead
            pergunta_id: ID da próxima pergunta
        """
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE leads 
            SET proxima_pergunta_id = ? 
            WHERE id = ?
        """, (pergunta_id, lead_id))
        conn.commit()
        conn.close()
    
    def get_lead_proxima_pergunta(self, lead_id):
        """
        Retorna o ID da próxima pergunta que a IA deve fazer
        
        Returns:
            str: ID da pergunta ou None
        """
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT proxima_pergunta_id FROM leads WHERE id = ?", (lead_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result['proxima_pergunta_id']:
            return result['proxima_pergunta_id']
        return None

    # =======================
    # MÉTRICAS
    # =======================
    def get_metrics_summary(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM leads")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM leads WHERE status = 'ganho'")
        ganhos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM leads WHERE status = 'perdido'")
        perdidos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM leads WHERE status = 'em_atendimento'")
        ativos = c.fetchone()[0]

        funil = {
            "novo": total - ganhos - perdidos - ativos,
            "em_atendimento": ativos,
            "ganho": ganhos,
            "perdido": perdidos
        }

        conn.close()
        return {
            "total_leads": total,
            "leads_ganhos": ganhos,
            "leads_perdidos": perdidos,
            "funil": funil
        }
    
    def get_ia_metrics(self):
        """
        ✨ NOVO: Retorna métricas específicas da IA
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        # Total de leads qualificados pela IA
        c.execute("SELECT COUNT(*) FROM leads WHERE ai_qualified = 1")
        total_qualificados = c.fetchone()[0]
        
        # Leads por classificação
        c.execute("""
            SELECT classification, COUNT(*) as count 
            FROM leads 
            WHERE ai_qualified = 1 
            GROUP BY classification
        """)
        por_classificacao = {row['classification']: row['count'] for row in c.fetchall()}
        
        # Leads VIP
        c.execute("SELECT COUNT(*) FROM leads WHERE prioridade = 'vip'")
        total_vip = c.fetchone()[0]
        
        # Score médio
        c.execute("SELECT AVG(qualification_score) FROM leads WHERE ai_qualified = 1")
        score_medio = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_qualificados_ia': total_qualificados,
            'por_classificacao': por_classificacao,
            'total_vip': total_vip,
            'score_medio': round(score_medio, 1)
        }