"""
Sistema de Alertas e Monitoramento de Performance
Versão simplificada - apenas alertas funcionais
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import json


class AlertSystem:
    """Sistema profissional de alertas e monitoramento"""
    
    # Configurações de SLA (em minutos)
    SLA_CONFIGS = {
        'primeira_resposta': {
            'warning': 15,
            'danger': 30,
            'critical': 60
        },
        'resposta_subsequente': {
            'warning': 30,
            'danger': 60,
            'critical': 120
        },
        'lead_assumido': {
            'warning': 15,
            'danger': 30,
            'critical': 60
        }
    }
    
    # Configurações de performance
    PERFORMANCE_THRESHOLDS = {
        'taxa_resposta_minima': 80,
        'tempo_medio_resposta': 60,
        'leads_por_dia_minimo': 3,
        'taxa_conversao_minima': 20
    }
    
    def __init__(self, db):
        self.db = db
        self._create_alerts_table()
    
    def _create_alerts_table(self):
        """Cria tabela de alertas se não existir"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                lead_id INTEGER,
                vendedor_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id),
                FOREIGN KEY (vendedor_id) REFERENCES users(id)
            )
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_severity 
            ON system_alerts(severity, resolved)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_vendedor 
            ON system_alerts(vendedor_id, resolved)
        ''')
        
        conn.commit()
        conn.close()
    
    def check_all_alerts(self) -> List[Dict[str, Any]]:
        """Verifica todos os tipos de alertas"""
        alerts = []
        
        # APENAS AS 4 VERIFICAÇÕES QUE FUNCIONAM:
        alerts.extend(self.check_first_response_sla())
        alerts.extend(self.check_assigned_no_response())
        alerts.extend(self.check_abandoned_leads())
        alerts.extend(self.check_low_performance())
        
        return alerts
    
    def check_first_response_sla(self) -> List[Dict[str, Any]]:
        """Verifica leads que precisam de primeira resposta"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        alerts = []
        now = datetime.now()
        
        c.execute('''
            SELECT l.*, u.name as vendedor_name
            FROM leads l
            LEFT JOIN users u ON l.assigned_to = u.id
            WHERE l.status = 'novo'
            AND l.assigned_to IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM messages m 
                WHERE m.lead_id = l.id 
                AND m.sender_type = 'vendedor'
            )
        ''')
        
        leads = [dict(row) for row in c.fetchall()]
        
        for lead in leads:
            created_at = datetime.fromisoformat(lead['created_at'])
            minutes_waiting = (now - created_at).total_seconds() / 60
            
            severity = self._get_sla_severity(minutes_waiting, 'primeira_resposta')
            
            if severity:
                alert = self._create_alert(
                    alert_type='sla_primeira_resposta',
                    severity=severity,
                    lead_id=lead['id'],
                    vendedor_id=lead['assigned_to'],
                    title=f"Lead sem resposta: {lead['name']}",
                    message=f"Lead aguardando primeira resposta há {int(minutes_waiting)} minutos",
                    data={
                        'lead_name': lead['name'],
                        'lead_phone': lead['phone'],
                        'vendedor_name': lead['vendedor_name'],
                        'minutes_waiting': int(minutes_waiting)
                    }
                )
                if alert:
                    alerts.append(alert)
        
        conn.close()
        return alerts
    
    def check_assigned_no_response(self) -> List[Dict[str, Any]]:
        """Verifica vendedores que assumiram lead mas não responderam"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        alerts = []
        now = datetime.now()
        
        c.execute('''
            SELECT 
                l.*,
                u.name as vendedor_name,
                ll.timestamp as assigned_at
            FROM leads l
            INNER JOIN users u ON l.assigned_to = u.id
            INNER JOIN lead_logs ll ON l.id = ll.lead_id
            WHERE ll.action = 'lead_atribuido'
            AND l.status IN ('novo', 'contatado')
            AND NOT EXISTS (
                SELECT 1 FROM messages m 
                WHERE m.lead_id = l.id 
                AND m.sender_type = 'vendedor'
                AND m.timestamp > ll.timestamp
            )
            ORDER BY ll.timestamp DESC
        ''')
        
        leads = [dict(row) for row in c.fetchall()]
        
        for lead in leads:
            assigned_at = datetime.fromisoformat(lead['assigned_at'])
            minutes_since_assigned = (now - assigned_at).total_seconds() / 60
            
            severity = self._get_sla_severity(minutes_since_assigned, 'lead_assumido')
            
            if severity:
                alert = self._create_alert(
                    alert_type='lead_assumido_sem_resposta',
                    severity=severity,
                    lead_id=lead['id'],
                    vendedor_id=lead['assigned_to'],
                    title=f"⚠️ Lead assumido sem resposta: {lead['vendedor_name']}",
                    message=f"{lead['vendedor_name']} assumiu lead mas não respondeu há {int(minutes_since_assigned)} minutos",
                    data={
                        'lead_name': lead['name'],
                        'vendedor_name': lead['vendedor_name'],
                        'minutes_since_assigned': int(minutes_since_assigned),
                        'action_suggestion': 'Considerar redistribuir lead'
                    }
                )
                if alert:
                    alerts.append(alert)
        
        conn.close()
        return alerts
    
    def check_abandoned_leads(self) -> List[Dict[str, Any]]:
        """Detecta leads que estão sem interação há muito tempo"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        alerts = []
        now = datetime.now()
        threshold_hours = 24
        
        c.execute('''
            SELECT 
                l.*,
                u.name as vendedor_name,
                MAX(m.timestamp) as last_interaction
            FROM leads l
            LEFT JOIN users u ON l.assigned_to = u.id
            LEFT JOIN messages m ON l.id = m.lead_id
            WHERE l.status NOT IN ('ganho', 'perdido')
            AND l.assigned_to IS NOT NULL
            GROUP BY l.id
            HAVING last_interaction < datetime('now', '-24 hours')
            OR last_interaction IS NULL
        ''')
        
        leads = [dict(row) for row in c.fetchall()]
        
        for lead in leads:
            if lead['last_interaction']:
                last_interaction = datetime.fromisoformat(lead['last_interaction'])
                hours_abandoned = (now - last_interaction).total_seconds() / 3600
            else:
                created_at = datetime.fromisoformat(lead['created_at'])
                hours_abandoned = (now - created_at).total_seconds() / 3600
            
            if hours_abandoned >= threshold_hours:
                alert = self._create_alert(
                    alert_type='lead_abandonado',
                    severity='warning' if hours_abandoned < 48 else 'danger',
                    lead_id=lead['id'],
                    vendedor_id=lead['assigned_to'],
                    title=f"Lead abandonado: {lead['name']}",
                    message=f"Lead sem interação há {int(hours_abandoned)} horas",
                    data={
                        'lead_name': lead['name'],
                        'vendedor_name': lead['vendedor_name'],
                        'hours_abandoned': int(hours_abandoned)
                    }
                )
                if alert:
                    alerts.append(alert)
        
        conn.close()
        return alerts
    
    def check_low_performance(self) -> List[Dict[str, Any]]:
        """Detecta vendedores com performance abaixo do esperado"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        alerts = []
        
        c.execute('''
            SELECT 
                u.id,
                u.name,
                COUNT(DISTINCT l.id) as total_leads,
                COUNT(DISTINCT CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM messages m 
                        WHERE m.lead_id = l.id 
                        AND m.sender_type = 'vendedor'
                    ) THEN l.id 
                END) as leads_respondidos
            FROM users u
            LEFT JOIN leads l ON u.id = l.assigned_to
            WHERE u.role = 'vendedor'
            AND l.created_at >= datetime('now', '-7 days')
            GROUP BY u.id
            HAVING total_leads > 0
        ''')
        
        vendedores = [dict(row) for row in c.fetchall()]
        
        for vendedor in vendedores:
            if vendedor['total_leads'] > 0:
                taxa_resposta = (vendedor['leads_respondidos'] / vendedor['total_leads']) * 100
                
                if taxa_resposta < self.PERFORMANCE_THRESHOLDS['taxa_resposta_minima']:
                    alert = self._create_alert(
                        alert_type='performance_baixa',
                        severity='warning' if taxa_resposta > 60 else 'danger',
                        vendedor_id=vendedor['id'],
                        title=f"⚠️ Performance baixa: {vendedor['name']}",
                        message=f"Taxa de resposta de {taxa_resposta:.1f}% (mínimo: {self.PERFORMANCE_THRESHOLDS['taxa_resposta_minima']}%)",
                        data={
                            'vendedor_name': vendedor['name'],
                            'taxa_resposta': taxa_resposta,
                            'total_leads': vendedor['total_leads'],
                            'leads_respondidos': vendedor['leads_respondidos']
                        }
                    )
                    if alert:
                        alerts.append(alert)
        
        conn.close()
        return alerts
    
    def _get_sla_severity(self, minutes: float, sla_type: str) -> str:
        """Determina severidade baseado no tempo"""
        config = self.SLA_CONFIGS.get(sla_type, {})
        
        if minutes >= config.get('critical', 999):
            return 'critical'
        elif minutes >= config.get('danger', 999):
            return 'danger'
        elif minutes >= config.get('warning', 999):
            return 'warning'
        
        return None
    
    def _create_alert(self, alert_type: str, severity: str, title: str, 
                     message: str, data: Dict, lead_id: int = None, 
                     vendedor_id: int = None) -> Dict[str, Any]:
        """Cria um alerta no banco de dados"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        # Verificar se alerta similar já existe
        c.execute('''
            SELECT id FROM system_alerts
            WHERE alert_type = ?
            AND lead_id = ?
            AND vendedor_id = ?
            AND resolved = 0
            AND created_at >= datetime('now', '-2 hours')
        ''', (alert_type, lead_id, vendedor_id))
        
        existing = c.fetchone()
        
        if existing:
            conn.close()
            return None
        
        # Criar novo alerta
        c.execute('''
            INSERT INTO system_alerts 
            (alert_type, severity, lead_id, vendedor_id, title, message, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (alert_type, severity, lead_id, vendedor_id, title, message, json.dumps(data)))
        
        alert_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return {
            'id': alert_id,
            'alert_type': alert_type,
            'severity': severity,
            'lead_id': lead_id,
            'vendedor_id': vendedor_id,
            'title': title,
            'message': message,
            'data': data,
            'created_at': datetime.now().isoformat()
        }
    
    def get_active_alerts(self, vendedor_id: int = None) -> List[Dict[str, Any]]:
        """Busca alertas ativos"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        if vendedor_id:
            c.execute('''
                SELECT * FROM system_alerts
                WHERE resolved = 0
                AND vendedor_id = ?
                ORDER BY 
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'danger' THEN 2
                        WHEN 'warning' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
            ''', (vendedor_id,))
        else:
            c.execute('''
                SELECT * FROM system_alerts
                WHERE resolved = 0
                ORDER BY 
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'danger' THEN 2
                        WHEN 'warning' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
            ''')
        
        alerts = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Parse JSON data
        for alert in alerts:
            if alert.get('data'):
                alert['data'] = json.loads(alert['data'])
        
        return alerts
    
    def resolve_alert(self, alert_id: int):
        """Marca alerta como resolvido"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        c.execute('''
            UPDATE system_alerts
            SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (alert_id,))
        
        conn.commit()
        conn.close()
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de alertas"""
        conn = self.db.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                severity,
                COUNT(*) as count
            FROM system_alerts
            WHERE resolved = 0
            GROUP BY severity
        ''')
        
        by_severity = {row['severity']: row['count'] for row in c.fetchall()}
        
        c.execute('''
            SELECT 
                alert_type,
                COUNT(*) as count
            FROM system_alerts
            WHERE resolved = 0
            GROUP BY alert_type
        ''')
        
        by_type = {row['alert_type']: row['count'] for row in c.fetchall()}
        
        conn.close()
        
        return {
            'total_active': sum(by_severity.values()),
            'by_severity': by_severity,
            'by_type': by_type
        }