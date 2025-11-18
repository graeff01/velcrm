import { useEffect, useState } from 'react';
import api from '../api';
import LeadModal from './LeadModal';
import { toast } from './Toast';
import TagBadge from "./TagBadge";
import '../styles/components/Kanban.css';
import { usePermissions } from '../contexts/PermissionsContext';

export default function Kanban({ user, onOpenLead }) {
  const { canAccessLead, isVendedor } = usePermissions();
  const [leads, setLeads] = useState([]);
  const [draggedLead, setDraggedLead] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [vendedorFilter, setVendedorFilter] = useState(null);
  const [vendedores, setVendedores] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    novo: 0,
    em_atendimento: 0,
    qualificado: 0,
    ganho: 0,
    perdido: 0
  });

  const stages = [
    { key: 'novo', label: '🆕 Novo', color: '#3b82f6' },
    { key: 'em_atendimento', label: '💬 Em Atendimento', color: '#f59e0b' },
    { key: 'qualificado', label: '⭐ Qualificado', color: '#8b5cf6' },
    { key: 'ganho', label: '✅ Ganho', color: '#10b981' },
    { key: 'perdido', label: '❌ Perdido', color: '#ef4444' },
  ];

  // ==========================
  // 🔁 CARREGA LEADS DO SERVIDOR
  // ==========================
  const loadLeads = async () => {
    try {
      setLoading(true); // ✅ Inicia loading
      
      // Buscar leads e vendedores em paralelo
      const [leadsData, vendedoresData] = await Promise.all([
        api.getLeads(),
        (user.role === 'admin' || user.role === 'gestor') ? api.getVendedores() : Promise.resolve([])
      ]);
      
      // 🔐 Filtrar leads baseado em permissões
      const filteredLeads = leadsData.filter(lead => canAccessLead(lead));
      
      setLeads(filteredLeads);
      calculateStats(filteredLeads);
      
      if (vendedoresData.length > 0) {
        setVendedores(vendedoresData);
      }
      
      // Feedback visual para vendedores
      if (isVendedor()) {
        console.log(`📋 Exibindo ${filteredLeads.length} leads atribuídos a você`);
      }
      
    } catch (error) {
      console.error('❌ Erro ao carregar leads:', error);
      toast.error('Erro ao carregar leads');
    } finally {
      setLoading(false); // ✅ SEMPRE desliga loading
    }
  };

  // ==========================
  // 📊 CALCULA ESTATÍSTICAS
  // ==========================
  const calculateStats = (leadsData) => {
    const newStats = {
      total: leadsData.length,
      novo: leadsData.filter(l => l.status === 'novo').length,
      em_atendimento: leadsData.filter(l => l.status === 'em_atendimento').length,
      qualificado: leadsData.filter(l => l.status === 'qualificado').length,
      ganho: leadsData.filter(l => l.status === 'ganho').length,
      perdido: leadsData.filter(l => l.status === 'perdido').length,
    };
    setStats(newStats);
  };

  useEffect(() => {
    loadLeads();
    
    // 🔄 Auto-refresh a cada 30 segundos
    const interval = setInterval(loadLeads, 30000);
    return () => clearInterval(interval);
  }, [user.id]);

  // ==========================
  // 🔍 FILTROS E BUSCA
  // ==========================
  const getFilteredLeads = () => {
    let filtered = leads;

    // Filtro por vendedor (admin/gestor)
    if (vendedorFilter) {
      filtered = filtered.filter(l => l.assigned_to === vendedorFilter);
    }

    // Filtro por status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(l => l.status === filterStatus);
    }

    // Busca por nome ou telefone
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(l => 
        l.name?.toLowerCase().includes(term) ||
        l.phone?.includes(searchTerm)
      );
    }

    return filtered;
  };

  // ==========================
  // 🎯 ARRASTAR E SOLTAR
  // ==========================
  const handleDragStart = (lead) => {
    // 🚫 Vendedor não pode arrastar leads de outros
    if (isVendedor() && lead.assigned_to !== user.id) {
      toast.warn('🚫 Você não pode mover leads de outros vendedores');
      return;
    }
    setDraggedLead(lead);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
  };

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over');
  };

  const handleDrop = async (status, e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    if (!draggedLead || draggedLead.status === status) {
      setDraggedLead(null);
      return;
    }

    // 🚫 Validação extra de permissões
    if (isVendedor() && draggedLead.assigned_to !== user.id) {
      toast.warn('🚫 Você não pode mover leads de outros vendedores');
      setDraggedLead(null);
      return;
    }

    try {
      await api.updateLeadStatus(draggedLead.id, status);
      
      // Atualiza localmente
      const updatedLeads = leads.map((l) => 
        l.id === draggedLead.id ? { ...l, status } : l
      );
      
      setLeads(updatedLeads);
      calculateStats(updatedLeads);
      
      const stageName = stages.find(s => s.key === status)?.label || status;
      toast.success(`✅ Lead movido para ${stageName}`);
      
    } catch (err) {
      console.error('❌ Erro ao atualizar status:', err);
      toast.error('Erro ao mover lead');
    } finally {
      setDraggedLead(null);
    }
  };

  // ==========================
  // 📦 RENDERIZA COLUNAS
  // ==========================
  const renderColumn = (stage) => {
    const filteredLeads = getFilteredLeads();
    const stageLeads = filteredLeads.filter((lead) => lead.status === stage.key);

    return (
      <div
        key={stage.key}
        className="kanban-column"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(stage.key, e)}
      >
        <div 
          className="kanban-column-header"
          style={{ borderTopColor: stage.color }}
        >
          <div className="column-title">
            <span className="column-emoji">{stage.label.split(' ')[0]}</span>
            <span className="column-name">{stage.label.substring(stage.label.indexOf(' ') + 1)}</span>
          </div>
          <span 
            className="column-count"
            style={{ backgroundColor: stage.color }}
          >
            {stageLeads.length}
          </span>
        </div>

        <div className="kanban-list">
          {loading ? (
            <div className="column-loading">
              <div className="spinner"></div>
              <p>Carregando...</p>
            </div>
          ) : stageLeads.length === 0 ? (
            <div className="column-empty">
              <span className="empty-icon">📭</span>
              <p>Nenhum lead</p>
            </div>
          ) : (
            stageLeads.map((lead) => (
              <LeadCard
                key={lead.id}
                lead={lead}
                user={user}
                onDragStart={() => handleDragStart(lead)}
                onSelect={setSelectedLead}
              />
            ))
          )}
        </div>
      </div>
    );
  };

  // ==========================
  // 🧱 RENDER PRINCIPAL
  // ==========================
  
  return (
    <>
      {/* 🔐 Indicador de Filtro por Perfil */}
      {isVendedor() && (
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '12px 20px',
          borderRadius: '10px',
          margin: '0 0 20px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)'
        }}>
          <span style={{ fontSize: '20px' }}>👤</span>
          <div>
            <strong style={{ display: 'block', marginBottom: '2px', color: '#fff' }}>
              Visualização Pessoal
            </strong>
            <span style={{ fontSize: '13px', opacity: 0.9, color: '#fff' }}>
              Você está vendo apenas os leads atribuídos a você ({leads.length} leads)
            </span>
          </div>
        </div>
      )}

      {/* TOOLBAR COM FILTROS */}
      <div className="kanban-toolbar">
        <div className="toolbar-left">
          <div className="kanban-stats-mini">
            <span className="stat-item">
              <strong>{stats.total}</strong> Total
            </span>
            <span className="stat-item success">
              <strong>{stats.ganho}</strong> Ganhos
            </span>
            <span className="stat-item danger">
              <strong>{stats.perdido}</strong> Perdidos
            </span>
          </div>
        </div>

        <div className="toolbar-right">
          {/* BUSCA */}
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Buscar lead..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            {searchTerm && (
              <button 
                className="clear-search"
                onClick={() => setSearchTerm('')}
                title="Limpar busca"
              >
                ✕
              </button>
            )}
          </div>

          {/* FILTRO POR VENDEDOR (admin/gestor) */}
          {(user.role === 'admin' || user.role === 'gestor') && vendedores.length > 0 && (
            <select
              value={vendedorFilter || ''}
              onChange={(e) => setVendedorFilter(e.target.value ? parseInt(e.target.value) : null)}
              className="filter-select"
              title="Filtrar por vendedor"
            >
              <option value="">Todos os vendedores</option>
              {vendedores.map(v => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.total_leads || 0} leads)
                </option>
              ))}
            </select>
          )}

          {/* FILTRO POR STATUS */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="filter-select"
            title="Filtrar por status"
          >
            <option value="all">Todos os status</option>
            {stages.map(stage => (
              <option key={stage.key} value={stage.key}>
                {stage.label}
              </option>
            ))}
          </select>

          {/* BOTÃO REFRESH */}
          <button 
            className="btn-refresh"
            onClick={loadLeads}
            disabled={loading}
            title="Atualizar leads"
          >
            {loading ? '⏳' : '🔄'}
          </button>
        </div>
      </div>

      {/* BOARD DO KANBAN */}
      <div className="kanban-board">
        {stages.map(renderColumn)}
      </div>

      {/* MODAL DE DETALHES */}
      {selectedLead && (
        <LeadModal
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onOpenChat={(lead) => {
            setSelectedLead(null);
            if (onOpenLead) {
              onOpenLead(lead);
            }
          }}
          onUpdate={loadLeads}
        />
      )}
    </>
  );
}

// ==============================
// 💳 COMPONENTE LEADCARD
// ==============================
function LeadCard({ lead, onDragStart, onSelect, user }) {
  const isDraggable = user.role !== 'vendedor' || lead.assigned_to === user.id;
  const isOwner = lead.assigned_to === user.id;

  // 📅 Tempo desde última interação
  const getTimeAgo = (date) => {
    if (!date) return '';
    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    return `${diffDays}d`;
  };

  // 🎨 Cor do card baseada na urgência
  const getUrgencyClass = () => {
    if (!lead.updated_at) return '';
    
    const hoursSinceUpdate = (new Date() - new Date(lead.updated_at)) / (1000 * 60 * 60);
    
    if (hoursSinceUpdate > 48) return 'urgent-high';
    if (hoursSinceUpdate > 24) return 'urgent-medium';
    return '';
  };

  return (
    <div
      className={`kanban-card ${!isDraggable ? 'blocked' : ''} ${getUrgencyClass()} ${isOwner ? 'is-owner' : ''}`}
      draggable={isDraggable}
      onDragStart={isDraggable ? onDragStart : undefined}
      onClick={() => onSelect(lead)}
      title={
        !isDraggable
          ? '🔒 Este lead pertence a outro vendedor'
          : '👆 Clique para ver detalhes ou arraste para mudar status'
      }
    >
      {/* HEADER DO CARD */}
      <div className="lead-card-header">
        <span className="lead-id">#{lead.id}</span>
        {isOwner && <span className="owner-badge">👤 Meu</span>}
        {lead.updated_at && (
          <span className="time-ago">{getTimeAgo(lead.updated_at)}</span>
        )}
      </div>

      {/* CORPO DO CARD */}
      <div className="lead-card-body">
        <strong className="lead-name">
          {lead.name || 'Lead sem nome'}
        </strong>
        <p className="lead-phone">📱 {lead.phone}</p>
        {lead.city && (
          <small className="lead-location">📍 {lead.city}</small>
        )}
      </div>

      {/* TAGS */}
      {lead.tags && lead.tags.length > 0 && (
        <div className="lead-tags">
          {lead.tags.slice(0, 2).map((tag) => (
            <TagBadge key={tag.id} tag={tag} />
          ))}
          {lead.tags.length > 2 && (
            <span className="more-tags">+{lead.tags.length - 2}</span>
          )}
        </div>
      )}

      {/* FOOTER DO CARD */}
      <div className="lead-card-footer">
        {lead.assigned_to_name && (
          <span className="assigned-to">
            👤 {lead.assigned_to_name}
          </span>
        )}
        {!isDraggable && (
          <span className="locked-icon" title="Bloqueado">🔒</span>
        )}
      </div>
    </div>
  );
}