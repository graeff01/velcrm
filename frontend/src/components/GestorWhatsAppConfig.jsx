import React, { useState, useEffect } from 'react';
import api from '../api';
import '../styles/components/GestorWhatsAppConfig.css';

export default function GestorWhatsAppConfig() {
  const [config, setConfig] = useState({
    phone: '',
    receive_critical: true,
    receive_danger: true,
    receive_warning: false
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [hasConfig, setHasConfig] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await api.get('/gestores/whatsapp-config');
      if (response.data && response.data.phone) {
        setConfig({
          phone: response.data.phone,
          receive_critical: response.data.receive_critical,
          receive_danger: response.data.receive_danger,
          receive_warning: response.data.receive_warning
        });
        setHasConfig(true);
      }
    } catch (error) {
      console.error('Erro ao carregar config:', error);
    }
  };

  // ✅ NOVA FUNÇÃO: Formata número enquanto digita
  const formatPhoneDisplay = (value) => {
    const numbers = value.replace(/\D/g, '');
    
    if (numbers.length === 0) return '';
    if (numbers.length <= 2) return `+${numbers}`;
    if (numbers.length <= 4) return `+${numbers.slice(0, 2)} ${numbers.slice(2)}`;
    if (numbers.length <= 13) {
      return `+${numbers.slice(0, 2)} ${numbers.slice(2, 4)} ${numbers.slice(4)}`;
    }
    return `+${numbers.slice(0, 2)} ${numbers.slice(2, 4)} ${numbers.slice(4, 13)}`;
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.post('/gestores/whatsapp-config', config);
      setMessage('✅ Configuração salva com sucesso!');
      setHasConfig(true);
    } catch (error) {
      setMessage('❌ Erro ao salvar configuração');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setLoading(true);
    setMessage('');

    try {
      await api.post('/gestores/whatsapp-config/test');
      setMessage('📱 Mensagem de teste enviada! Verifique seu WhatsApp.');
    } catch (error) {
      setMessage('❌ Erro ao enviar teste');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    if (!window.confirm('Deseja realmente desativar as notificações?')) return;

    setLoading(true);
    try {
      await api.delete('/gestores/whatsapp-config');
      setMessage('✅ Notificações desativadas');
      setConfig({ ...config, phone: '' });
      setHasConfig(false);
    } catch (error) {
      setMessage('❌ Erro ao desativar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="whatsapp-config-container">
      <div className="config-header">
        <h2>📱 Notificações WhatsApp</h2>
        <p>Receba alertas críticos diretamente no seu WhatsApp</p>
      </div>

      <form onSubmit={handleSave} className="config-form">
        <div className="form-group">
          <label>
            📞 Número do WhatsApp
            <span className="hint">(formato: +55 51 994003224)</span>
          </label>
          <input
            type="tel"
            placeholder="+55 51 994003224"
            value={formatPhoneDisplay(config.phone)}
            onChange={(e) => {
              const numbers = e.target.value.replace(/\D/g, '');
              setConfig({ ...config, phone: numbers });
            }}
            maxLength="17"
            required
          />
        </div>

        <div className="form-section">
          <h3>🔔 Tipos de Alertas</h3>
          
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={config.receive_critical}
              onChange={(e) => setConfig({ ...config, receive_critical: e.target.checked })}
            />
            <div>
              <strong>🚨 Críticos</strong>
              <span>Leads urgentes sem resposta (&gt;60min)</span>
            </div>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={config.receive_danger}
              onChange={(e) => setConfig({ ...config, receive_danger: e.target.checked })}
            />
            <div>
              <strong>⚠️ Urgentes</strong>
              <span>Leads sem resposta (&gt;30min)</span>
            </div>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={config.receive_warning}
              onChange={(e) => setConfig({ ...config, receive_warning: e.target.checked })}
            />
            <div>
              <strong>⚡ Avisos</strong>
              <span>Alertas gerais de performance</span>
            </div>
          </label>
        </div>

        {message && (
          <div className={`message ${message.includes('❌') ? 'error' : 'success'}`}>
            {message}
          </div>
        )}

        <div className="button-group">
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Salvando...' : '💾 Salvar Configuração'}
          </button>

          {hasConfig && (
            <>
              <button type="button" onClick={handleTest} disabled={loading} className="btn-secondary">
                📱 Enviar Teste
              </button>
              <button type="button" onClick={handleDisable} disabled={loading} className="btn-danger">
                🔕 Desativar
              </button>
            </>
          )}
        </div>
      </form>

      <div className="config-info">
        <h4>ℹ️ Como funciona:</h4>
        <ul>
          <li>✅ Você receberá mensagens automáticas quando houver alertas</li>
          <li>⏰ Horário silencioso: 22h às 8h (configurável)</li>
          <li>🔒 Seu número fica privado e seguro</li>
          <li>📱 Funciona com WhatsApp pessoal ou Business</li>
        </ul>
      </div>
    </div>
  );
}