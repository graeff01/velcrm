import { Clock, MessageSquare, Star, Zap, User } from "lucide-react";
import "../styles/components/LeadCard.css";

export default function LeadCard({ lead, onClick, currentUser }) {
  // Recebe currentUser como prop ao invés de usar useAuth
  const isAdminOrGestor = currentUser && ['admin', 'gestor'].includes(currentUser.role);
  
  // Calcular tempo desde última interação
  const getTempoDecorrido = (timestamp) => {
    if (!timestamp) return 'Sem mensagens';
    
    const agora = new Date();
    const data = new Date(timestamp);
    const diff = Math.floor((agora - data) / 1000); // segundos
    
    if (diff < 60) return 'Agora mesmo';
    if (diff < 3600) return `${Math.floor(diff / 60)}min atrás`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
    return `${Math.floor(diff / 86400)}d atrás`;
  };
  
  // Score visual
  const getScoreColor = (score) => {
    if (score >= 70) return 'score-green';
    if (score >= 40) return 'score-yellow';
    return 'score-red';
  };
  
  // Status labels
  const STATUS_LABELS = {
    'novo': 'Novo',
    'em_atendimento': 'Em Atendimento',
    'qualificado': 'Qualificado',
    'negociacao': 'Negociação',
    'ganho': 'Ganho',
    'perdido': 'Perdido'
  };
  
  // Budget labels
  const BUDGET_LABELS = {
    'baixo': 'Até R$ 2.000',
    'medio': 'R$ 2.000 - R$ 5.000',
    'alto': 'R$ 5.000 - R$ 10.000',
    'premium': 'Acima de R$ 10.000'
  };
  
  // Urgency icons
  const URGENCY_ICONS = {
    'imediato': '🔥',
    'urgente': '⚡',
    'normal': ''
  };
  
  const onDragStart = (e) => {
    e.dataTransfer.setData('leadId', lead.id);
  };
  
  return (
    <div 
      className={`lead-card-premium ${lead.priority || ''}`}
      draggable 
      onDragStart={onDragStart}
      onClick={onClick}
    >
      {/* Priority indicator */}
      <div className={`priority-indicator priority-${lead.priority || 'normal'}`} />
      
      {/* Header */}
      <div className="lead-card-header">
        <span className={`status-badge status-${lead.status}`}>
          {STATUS_LABELS[lead.status] || lead.status}
        </span>
        
        <div className="badges-group">
          {lead.priority === 'vip' && (
            <span className="priority-badge vip">
              <Star size={12} fill="currentColor" /> VIP
            </span>
          )}
          
          {lead.urgency && lead.urgency !== 'normal' && (
            <span className={`urgency-badge urgency-${lead.urgency}`}>
              {URGENCY_ICONS[lead.urgency]} {lead.urgency === 'imediato' ? 'Urgente' : 'Alta'}
            </span>
          )}
        </div>
      </div>
      
      {/* Lead Info */}
      <div className="lead-info-section">
        <h3 className="lead-name">{lead.name || 'Lead sem nome'}</h3>
        <span className="lead-phone">{formatPhone(lead.phone)}</span>
      </div>
      
      {/* VENDEDOR INFO - Apenas para Admin/Gestor */}
      {isAdminOrGestor && (
        <div className="vendedor-info-card">
          {lead.assigned_to ? (
            <>
              <div className="vendedor-avatar">
                {(lead.assigned_to_name || 'V').charAt(0).toUpperCase()}
              </div>
              <div className="vendedor-details">
                <span className="vendedor-label">Atendido por:</span>
                <span className="vendedor-name">{lead.assigned_to_name || 'Vendedor'}</span>
              </div>
            </>
          ) : (
            <div className="vendedor-sem-atribuir">
              <User size={14} />
              <span>Aguardando atribuição</span>
            </div>
          )}
        </div>
      )}
      
      {/* Metrics Grid */}
      <div className="lead-metrics-grid">
        {/* Score */}
        {lead.lead_score !== undefined && (
          <div className="metric-item">
            <span className="metric-label">Score</span>
            <span className={`metric-value score-badge ${getScoreColor(lead.lead_score)}`}>
              {lead.lead_score}/100
            </span>
          </div>
        )}
        
        {/* Última interação */}
        <div className="metric-item">
          <span className="metric-label">
            <Clock size={12} /> Última msg
          </span>
          <span className="metric-value metric-time">
            {getTempoDecorrido(lead.last_message_at || lead.updated_at)}
          </span>
        </div>
        
        {/* Total de mensagens */}
        <div className="metric-item">
          <span className="metric-label">
            <MessageSquare size={12} /> Mensagens
          </span>
          <span className="metric-value">
            {lead.message_count || 0}
          </span>
        </div>
      </div>
      
      {/* Tags inline */}
      {lead.tags && lead.tags.length > 0 && (
        <div className="tags-inline">
          {lead.tags.slice(0, 3).map((tag) => (
            <span 
              key={tag.id} 
              className="tag-mini"
              style={{ backgroundColor: tag.color }}
            >
              {tag.name}
            </span>
          ))}
          {lead.tags.length > 3 && (
            <span className="tag-more">+{lead.tags.length - 3}</span>
          )}
        </div>
      )}
      
      {/* Budget */}
      {lead.budget_range && (
        <div className="lead-budget-inline">
          💰 {BUDGET_LABELS[lead.budget_range] || lead.budget_range}
        </div>
      )}
      
      {/* Origem/Cidade */}
      <div className="lead-metadata">
        {lead.origem && <span className="meta-item">📍 {lead.origem}</span>}
        {lead.city && <span className="meta-item">🌆 {lead.city}</span>}
      </div>
      
      {/* Footer */}
      <div className="lead-card-footer">
        <span className="lead-id">#{lead.id}</span>
        {lead.triage_status === 'qualificado' && (
          <span className="qualified-badge">
            <Zap size={12} /> Qualificado IA
          </span>
        )}
      </div>
    </div>
  );
}

// Helper function
function formatPhone(phone) {
  if (!phone) return '';
  
  // Remove tudo exceto números
  const numbers = phone.replace(/\D/g, '');
  
  // Formata como (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
  if (numbers.length === 13) {
    return `+${numbers.slice(0, 2)} (${numbers.slice(2, 4)}) ${numbers.slice(4, 9)}-${numbers.slice(9)}`;
  }
  if (numbers.length === 11) {
    return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7)}`;
  }
  if (numbers.length === 10) {
    return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 6)}-${numbers.slice(6)}`;
  }
  
  return phone;
}