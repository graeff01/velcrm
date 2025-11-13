"""
🗄️ DATABASE IA - Extensões para IA Assistant
Adiciona tabelas e métodos para qualificação de leads por IA
"""

def extend_database_with_ia(db):
    """
    Estende o banco de dados com tabelas para IA

    Tabelas criadas:
    - lead_qualificacao: Respostas das perguntas de qualificação
    - lead_ia_state: Estado da conversa com IA (pergunta atual, etc)
    """
    conn = db.get_connection()
    c = conn.cursor()

    # Tabela de qualificação de leads
    c.execute("""
        CREATE TABLE IF NOT EXISTS lead_qualificacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            pergunta_id TEXT NOT NULL,
            resposta TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id),
            UNIQUE(lead_id, pergunta_id)
        )
    """)

    # Tabela de estado da IA para cada lead
    c.execute("""
        CREATE TABLE IF NOT EXISTS lead_ia_state (
            lead_id INTEGER PRIMARY KEY,
            proxima_pergunta_id TEXT,
            mensagens_ia_count INTEGER DEFAULT 0,
            qualificado_em DATETIME,
            escalado_humano INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    # Índices para performance
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_lead_qualificacao_lead_id
        ON lead_qualificacao(lead_id)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_lead_ia_state_proxima_pergunta
        ON lead_ia_state(proxima_pergunta_id)
    """)

    conn.commit()
    conn.close()

    print("✅ Tabelas de IA criadas com sucesso!")

    # Adicionar métodos ao Database
    _adicionar_metodos_ia(db)

def _adicionar_metodos_ia(db):
    """Adiciona métodos de IA ao objeto Database"""

    def add_lead_qualificacao_resposta(lead_id, pergunta_id, resposta):
        """Adiciona resposta de qualificação"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO lead_qualificacao
                (lead_id, pergunta_id, resposta)
                VALUES (?, ?, ?)
            """, (lead_id, pergunta_id, resposta))
            conn.commit()
        finally:
            conn.close()

    def get_lead_qualificacao_respostas(lead_id):
        """Retorna todas as respostas de qualificação de um lead"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT * FROM lead_qualificacao
                WHERE lead_id = ?
                ORDER BY created_at ASC
            """, (lead_id,))
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def set_lead_proxima_pergunta(lead_id, pergunta_id):
        """Define qual será a próxima pergunta para o lead"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO lead_ia_state
                (lead_id, proxima_pergunta_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (lead_id, pergunta_id))
            conn.commit()
        finally:
            conn.close()

    def get_lead_proxima_pergunta(lead_id):
        """Retorna ID da próxima pergunta aguardando resposta"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT proxima_pergunta_id FROM lead_ia_state
                WHERE lead_id = ?
            """, (lead_id,))
            result = c.fetchone()
            return result['proxima_pergunta_id'] if result else None
        finally:
            conn.close()

    def increment_ia_message_count(lead_id):
        """Incrementa contador de mensagens da IA"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO lead_ia_state (lead_id, mensagens_ia_count)
                VALUES (?, 1)
                ON CONFLICT(lead_id) DO UPDATE
                SET mensagens_ia_count = mensagens_ia_count + 1
            """, (lead_id,))
            conn.commit()
        finally:
            conn.close()

    def get_ia_message_count(lead_id):
        """Retorna quantas mensagens a IA já enviou"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT mensagens_ia_count FROM lead_ia_state
                WHERE lead_id = ?
            """, (lead_id,))
            result = c.fetchone()
            return result['mensagens_ia_count'] if result else 0
        finally:
            conn.close()

    def marcar_lead_escalado_humano(lead_id):
        """Marca que lead foi escalado para humano"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO lead_ia_state (lead_id, escalado_humano)
                VALUES (?, 1)
                ON CONFLICT(lead_id) DO UPDATE
                SET escalado_humano = 1, updated_at = CURRENT_TIMESTAMP
            """, (lead_id,))
            conn.commit()
        finally:
            conn.close()

    def lead_foi_escalado_humano(lead_id):
        """Verifica se lead já foi escalado"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT escalado_humano FROM lead_ia_state
                WHERE lead_id = ?
            """, (lead_id,))
            result = c.fetchone()
            return bool(result and result['escalado_humano']) if result else False
        finally:
            conn.close()

    def get_leads_qualificados_ia():
        """Retorna leads qualificados pela IA (prontos para atendimento)"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT l.*, COUNT(q.id) as respostas_coletadas
                FROM leads l
                INNER JOIN lead_ia_state s ON l.id = s.lead_id
                LEFT JOIN lead_qualificacao q ON l.id = q.lead_id
                WHERE l.status = 'qualificado'
                AND s.qualificado_em IS NOT NULL
                AND l.assigned_to IS NULL
                GROUP BY l.id
                ORDER BY s.qualificado_em DESC
            """)
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def get_estatisticas_ia():
        """Retorna estatísticas da IA"""
        conn = db.get_connection()
        c = conn.cursor()
        try:
            # Total de leads que interagiram com IA
            c.execute("SELECT COUNT(*) as total FROM lead_ia_state")
            total_interacoes = c.fetchone()['total']

            # Total qualificados pela IA
            c.execute("""
                SELECT COUNT(*) as total FROM lead_ia_state
                WHERE qualificado_em IS NOT NULL
            """)
            total_qualificados = c.fetchone()['total']

            # Total escalados para humano
            c.execute("""
                SELECT COUNT(*) as total FROM lead_ia_state
                WHERE escalado_humano = 1
            """)
            total_escalados = c.fetchone()['total']

            # Média de mensagens por lead
            c.execute("""
                SELECT AVG(mensagens_ia_count) as media
                FROM lead_ia_state
                WHERE mensagens_ia_count > 0
            """)
            media_mensagens = c.fetchone()['media'] or 0

            return {
                "total_interacoes": total_interacoes,
                "total_qualificados": total_qualificados,
                "total_escalados": total_escalados,
                "taxa_qualificacao": round((total_qualificados / total_interacoes * 100) if total_interacoes > 0 else 0, 1),
                "media_mensagens_por_lead": round(media_mensagens, 1)
            }
        finally:
            conn.close()

    # Adicionar métodos ao objeto Database
    db.add_lead_qualificacao_resposta = add_lead_qualificacao_resposta
    db.get_lead_qualificacao_respostas = get_lead_qualificacao_respostas
    db.set_lead_proxima_pergunta = set_lead_proxima_pergunta
    db.get_lead_proxima_pergunta = get_lead_proxima_pergunta
    db.increment_ia_message_count = increment_ia_message_count
    db.get_ia_message_count = get_ia_message_count
    db.marcar_lead_escalado_humano = marcar_lead_escalado_humano
    db.lead_foi_escalado_humano = lead_foi_escalado_humano
    db.get_leads_qualificados_ia = get_leads_qualificados_ia
    db.get_estatisticas_ia = get_estatisticas_ia

    print("✅ Métodos de IA adicionados ao Database!")
