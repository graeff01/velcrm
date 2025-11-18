"""
🌐 NOVAS ROTAS DA API
Adicione estas rotas ao seu app.py

INSTRUÇÕES:
1. Copie este código
2. Cole no final do seu app.py (antes do if __name__ == "__main__")
3. Importe as novas classes no topo
"""

# ===== ADICIONAR NO TOPO DO app.py =====
from triagem_inteligente import TriagemInteligente
from automacoes_poderosas import AutomacoesPoderosas

# ===== NO LUGAR ONDE VOCÊ INICIALIZA O IA ASSISTANT =====
# Após criar ia_assistant, adicione:
triagem = TriagemInteligente(db, ia_assistant)
automacoes = AutomacoesPoderosas(db, whatsapp_service)

# ===== ADICIONAR ESTAS ROTAS =====

# ============================================
# 🔍 ROTAS DE TRIAGEM
# ============================================

@app.route('/api/triagem/metricas', methods=['GET'])
@login_required
def get_triagem_metricas():
    """Retorna métricas do sistema de triagem"""
    try:
        metricas = triagem.get_metricas_triagem()
        return jsonify(metricas), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/triagem/lead/<int:lead_id>/finalizar', methods=['POST'])
@login_required
@role_required(['admin', 'gestor'])
def finalizar_triagem_manual(lead_id):
    """Permite finalizar triagem manualmente"""
    try:
        motivo = request.json.get('motivo', 'manual')
        success = triagem.finalizar_triagem(lead_id, motivo)
        
        if success:
            return jsonify({'message': 'Triagem finalizada'}), 200
        else:
            return jsonify({'error': 'Falha ao finalizar'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# 📋 ROTAS DE FILA INTELIGENTE
# ============================================

@app.route('/api/fila/inteligente', methods=['GET'])
@login_required
def get_fila_inteligente():
    """Retorna fila ordenada por prioridade e score"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Buscar leads da fila inteligente
        c.execute("""
            SELECT 
                l.*,
                CASE 
                    WHEN l.priority = 'vip' THEN 1000
                    WHEN l.priority = 'alta' THEN 100
                    WHEN l.priority = 'normal' THEN 10
                    ELSE 1
                END + l.lead_score as ranking_score,
                CASE
                    WHEN l.urgency = 'imediato' THEN '🔥'
                    WHEN l.urgency = 'urgente' THEN '⚡'
                    WHEN l.priority = 'vip' THEN '👑'
                    ELSE '📋'
                END as emoji_icon
            FROM leads l
            WHERE l.triage_status = 'qualificado'
              AND l.assigned_to IS NULL
              AND l.status NOT IN ('ganho', 'perdido')
            ORDER BY ranking_score DESC, l.created_at ASC
            LIMIT 50
        """)
        
        leads = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(leads), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fila/por-prioridade', methods=['GET'])
@login_required
def get_fila_por_prioridade():
    """Retorna leads agrupados por prioridade"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # VIP
        c.execute("""
            SELECT * FROM leads
            WHERE triage_status = 'qualificado'
              AND priority = 'vip'
              AND assigned_to IS NULL
              AND status NOT IN ('ganho', 'perdido')
            ORDER BY lead_score DESC, created_at ASC
        """)
        vips = [dict(row) for row in c.fetchall()]
        
        # Alta Prioridade
        c.execute("""
            SELECT * FROM leads
            WHERE triage_status = 'qualificado'
              AND priority = 'alta'
              AND assigned_to IS NULL
              AND status NOT IN ('ganho', 'perdido')
            ORDER BY lead_score DESC, created_at ASC
        """)
        alta = [dict(row) for row in c.fetchall()]
        
        # Normal
        c.execute("""
            SELECT * FROM leads
            WHERE triage_status = 'qualificado'
              AND priority = 'normal'
              AND assigned_to IS NULL
              AND status NOT IN ('ganho', 'perdido')
            ORDER BY lead_score DESC, created_at ASC
        """)
        normal = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'vip': vips,
            'alta': alta,
            'normal': normal,
            'total': len(vips) + len(alta) + len(normal)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# 🤖 ROTAS DE AUTOMAÇÕES
# ============================================

@app.route('/api/automacoes/metricas', methods=['GET'])
@login_required
@role_required(['admin', 'gestor'])
def get_automacoes_metricas():
    """Retorna métricas das automações"""
    try:
        metricas = automacoes.get_estatisticas()
        return jsonify(metricas), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/automacoes/lead/<int:lead_id>/agendar-followup', methods=['POST'])
@login_required
def agendar_followup_manual(lead_id):
    """Agenda follow-up manualmente"""
    try:
        delay_horas = request.json.get('delay_horas', 24)
        success = automacoes.agendar_followup(lead_id, delay_horas=delay_horas)
        
        if success:
            return jsonify({'message': 'Follow-up agendado'}), 200
        else:
            return jsonify({'error': 'Falha ao agendar'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/automacoes/lead/<int:lead_id>/cancelar', methods=['POST'])
@login_required
def cancelar_automacoes_manual(lead_id):
    """Cancela automações de um lead"""
    try:
        success = automacoes.cancelar_automacoes_lead(lead_id)
        
        if success:
            return jsonify({'message': 'Automações canceladas'}), 200
        else:
            return jsonify({'error': 'Falha ao cancelar'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# 📊 ROTA DE MÉTRICAS COMPLETAS
# ============================================

@app.route('/api/metricas/completas', methods=['GET'])
@login_required
@role_required(['admin', 'gestor'])
def get_metricas_completas():
    """Retorna todas as métricas do sistema"""
    try:
        metricas_ia = ia_assistant.get_estatisticas()
        metricas_triagem = triagem.get_metricas_triagem()
        metricas_automacoes = automacoes.get_estatisticas()
        
        # Métricas gerais de leads
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM leads")
        total_leads = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM leads WHERE status = 'ganho'")
        ganhos = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM leads WHERE assigned_to IS NOT NULL")
        em_atendimento = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'ia': metricas_ia,
            'triagem': metricas_triagem,
            'automacoes': metricas_automacoes,
            'geral': {
                'total_leads': total_leads,
                'ganhos': ganhos,
                'em_atendimento': em_atendimento,
                'taxa_conversao': round((ganhos / total_leads * 100) if total_leads > 0 else 0, 1)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# 🔄 ATUALIZAR ROTA EXISTENTE /api/leads/queue
# ============================================

# SUBSTITUA a rota /api/leads/queue existente por esta:

@app.route('/api/leads/queue', methods=['GET'])
@login_required
def get_leads_queue_upgraded():
    """Retorna fila de leads (VERSÃO MELHORADA)"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Buscar apenas leads QUALIFICADOS pela triagem
        c.execute("""
            SELECT 
                l.*,
                l.lead_score,
                l.priority,
                l.urgency,
                l.budget_range,
                CASE 
                    WHEN l.priority = 'vip' THEN 1000
                    WHEN l.priority = 'alta' THEN 100
                    WHEN l.priority = 'normal' THEN 10
                    ELSE 1
                END + l.lead_score as ranking_score
            FROM leads l
            WHERE l.triage_status = 'qualificado'
              AND l.assigned_to IS NULL
              AND l.status NOT IN ('ganho', 'perdido')
            ORDER BY ranking_score DESC, l.created_at ASC
        """)
        
        leads = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(leads), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500