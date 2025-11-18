import { useState, useEffect } from 'react';
import { 
  Bot, 
  TrendingUp, 
  Users, 
  MessageSquare, 
  Clock, 
  Target,
  CheckCircle,
  AlertTriangle,
  Settings,
  RefreshCw,
  Zap
} from 'lucide-react';
import api from '../api';
import '../styles/components/IADashboard.css';

export default function IADashboard({ currentUser }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [iaStatus, setIaStatus] = useState(null);
  const [leadsQualificados, setLeadsQualificados] = useState([]);
  const [triagem, setTriagem] = useState(null);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Carregar status da IA
      const statusResponse = await fetch('/api/ia/status', {
        credentials: 'include'
      });
      const statusData = await statusResponse.json();
      setIaStatus(statusData);

      // Carregar leads qualificados (apenas admin/gestor)
      if (currentUser.role !== 'vendedor') {
        const leadsResponse = await fetch('/api/ia/leads-qualificados', {
          credentials: 'include'
        });
        const leadsData = await leadsResponse.json();
        setLeadsQualificados(leadsData);

        // Carregar métricas de triagem
        const triagemResponse = await fetch('/api/triagem/metricas', {
          credentials: 'include'
        });
        const triagemData = await triagemResponse.json();
        setTriagem(triagemData);
      }

    } catch (error) {
      console.error('Erro ao carregar dashboard IA:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const handleToggleIA = async () => {
    // TODO: Implementar endpoint para ligar/desligar IA
    alert('Funcionalidade em desenvolvimento');
  };

  const formatNumber = (num) => {
    return num?.toLocaleString('pt-BR') || '0';
  };

  if (loading) {
    return (
      <div className="ia-dashboard-loading">
        <div className="spinner-large"></div>
        <p>Carregando Dashboard da IA...</p>
      </div>
    );
  }

  if (!iaStatus?.habilitada) {
    return (
      <div className="ia-dashboard-disabled">
        <Bot size={64} className="icon-disabled" />
        <h2>IA Assistant Desabilitada</h2>
        <p>A Inteligência Artificial não está configurada neste sistema.</p>
        <p className="ia-reason">{iaStatus?.motivo || 'Configure a API Key da OpenAI para ativar'}</p>
      </div>
    );
  }

  const stats = iaStatus?.estatisticas || {};
  const config = iaStatus?.configuracao || {};

  return (
    <div className="ia-dashboard">
      {/* Header */}
      <div className="ia-header">
        <div className="ia-header-left">
          <div className="ia-header-icon">
            <Bot size={32} />
          </div>
          <div>
            <h1>🤖 IA Assistant Dashboard</h1>
            <p>Sistema de Qualificação Automática de Leads</p>
          </div>
        </div>
        
        <div className="ia-header-right">
          <button 
            className="btn-refresh" 
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={18} className={refreshing ? 'spinning' : ''} />
            Atualizar
          </button>
          
          {currentUser.role === 'admin' && (
            <button 
              className="btn-config"
              onClick={() => setShowConfig(!showConfig)}
            >
              <Settings size={18} />
              Configurar
            </button>
          )}
        </div>
      </div>

      {/* Status Banner */}
      <div className="ia-status-banner active">
        <div className="status-indicator">
          <Zap size={20} />
          <span>IA ATIVA</span>
        </div>
        <div className="status-info">
          <span>Modelo: {config.modelo || 'gpt-4o-mini'}</span>
          <span>•</span>
          <span>OpenAI: {config.openai_disponivel ? '✅ Conectada' : '❌ Offline'}</span>
        </div>
      </div>

      {/* Grid de Métricas */}
      <div className="ia-metrics-grid">
        {/* Total de Interações */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(59, 130, 246, 0.1)' }}>
            <MessageSquare size={24} style={{ color: '#3b82f6' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatNumber(stats.total_interacoes)}</div>
            <div className="metric-label">Total de Interações</div>
          </div>
        </div>

        {/* Leads Qualificados */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
            <CheckCircle size={24} style={{ color: '#10b981' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatNumber(stats.total_qualificados)}</div>
            <div className="metric-label">Leads Qualificados</div>
          </div>
        </div>

        {/* Taxa de Qualificação */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(0, 168, 132, 0.1)' }}>
            <Target size={24} style={{ color: '#00a884' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{stats.taxa_qualificacao || 0}%</div>
            <div className="metric-label">Taxa de Conversão</div>
          </div>
        </div>

        {/* Escalados para Humano */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(245, 158, 11, 0.1)' }}>
            <Users size={24} style={{ color: '#f59e0b' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatNumber(stats.total_escalados)}</div>
            <div className="metric-label">Escalados p/ Humano</div>
          </div>
        </div>

        {/* Média de Mensagens */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
            <MessageSquare size={24} style={{ color: '#8b5cf6' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{stats.media_mensagens_por_lead || 0}</div>
            <div className="metric-label">Média de Mensagens</div>
          </div>
        </div>

        {/* Perguntas Cadastradas */}
        <div className="ia-metric-card">
          <div className="metric-icon" style={{ background: 'rgba(236, 72, 153, 0.1)' }}>
            <MessageSquare size={24} style={{ color: '#ec4899' }} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{config.total_perguntas || 0}</div>
            <div className="metric-label">Perguntas Cadastradas</div>
          </div>
        </div>
      </div>

      {/* Métricas de Triagem (Admin/Gestor) */}
      {currentUser.role !== 'vendedor' && triagem && (
        <div className="ia-triagem-section">
          <h3>📊 Sistema de Triagem Inteligente</h3>
          
          <div className="triagem-grid">
            <div className="triagem-card">
              <div className="triagem-header">
                <Clock size={20} />
                <span>Em Triagem</span>
              </div>
              <div className="triagem-value">{triagem.em_triagem || 0}</div>
            </div>

            <div className="triagem-card">
              <div className="triagem-header">
                <CheckCircle size={20} />
                <span>Qualificados Hoje</span>
              </div>
              <div className="triagem-value">{triagem.qualificados_hoje || 0}</div>
            </div>

            <div className="triagem-card">
              <div className="triagem-header">
                <TrendingUp size={20} />
                <span>Score Médio</span>
              </div>
              <div className="triagem-value">{triagem.score_medio || 0}</div>
            </div>

            <div className="triagem-card priority-vip">
              <div className="triagem-header">
                <Zap size={20} />
                <span>VIP</span>
              </div>
              <div className="triagem-value">{triagem.vips || 0}</div>
            </div>

            <div className="triagem-card priority-alta">
              <div className="triagem-header">
                <AlertTriangle size={20} />
                <span>Alta Prioridade</span>
              </div>
              <div className="triagem-value">{triagem.alta_prioridade || 0}</div>
            </div>

            <div className="triagem-card priority-normal">
              <div className="triagem-header">
                <Target size={20} />
                <span>Normal</span>
              </div>
              <div className="triagem-value">{triagem.normal || 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Lista de Leads Qualificados */}
      {currentUser.role !== 'vendedor' && (
        <div className="ia-leads-section">
          <div className="section-header">
            <h3>🎯 Leads Qualificados pela IA</h3>
            <span className="leads-count">{leadsQualificados.length} leads</span>
          </div>

          {leadsQualificados.length === 0 ? (
            <div className="empty-state">
              <CheckCircle size={48} style={{ opacity: 0.3 }} />
              <p>Nenhum lead qualificado aguardando atribuição</p>
            </div>
          ) : (
            <div className="leads-list-ia">
              {leadsQualificados.map(lead => (
                <div key={lead.id} className="lead-card-ia">
                  <div className="lead-info">
                    <div className="lead-header">
                      <span className="lead-name">{lead.name}</span>
                      <span className={`lead-priority priority-${lead.priority || 'normal'}`}>
                        {lead.priority?.toUpperCase() || 'NORMAL'}
                      </span>
                    </div>
                    
                    <div className="lead-meta">
                      <span className="lead-phone">📱 {lead.phone}</span>
                      <span className="lead-score">Score: {lead.lead_score || 0}</span>
                    </div>

                    <div className="lead-qualificacao">
                      <span className="respostas-count">
                        {lead.respostas_coletadas || 0} respostas coletadas
                      </span>
                    </div>
                  </div>

                  <div className="lead-actions">
                    <button 
                      className="btn-view-lead"
                      onClick={() => window.location.href = `/leads/${lead.id}`}
                    >
                      Ver Detalhes
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Configurações (apenas Admin) */}
      {showConfig && currentUser.role === 'admin' && (
        <div className="ia-config-panel">
          <h3>⚙️ Configurações da IA</h3>
          <div className="config-info">
            <p><strong>Modelo:</strong> {config.modelo}</p>
            <p><strong>Perguntas:</strong> {config.total_perguntas}</p>
            <p><strong>Status:</strong> {config.openai_disponivel ? '✅ Ativa' : '❌ Offline'}</p>
          </div>
          <p className="config-note">
            Para editar configurações avançadas, edite o arquivo <code>ia_config.json</code> no backend.
          </p>
        </div>
      )}
    </div>
  );
}