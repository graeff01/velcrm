import React, { useState } from 'react';
import { Download, FileText, Table, File } from 'lucide-react';
import '../styles/components/ExportButtons.css';

export default function ExportButtons({ period, vendedorId, currentUser }) {
  const [loading, setLoading] = useState(false);

  const handleExport = async (type) => {
    setLoading(true);
    try {
      let url = '';
      
      if (type === 'metrics-pdf') {
        url = `http://localhost:5000/api/export/metrics/pdf?period=${period}`;
        if (vendedorId) url += `&vendedor_id=${vendedorId}`;
      } else if (type === 'leads-excel') {
        url = `http://localhost:5000/api/export/leads/excel`;
        if (vendedorId) url += `?vendedor_id=${vendedorId}`;
      } else if (type === 'leads-csv') {
        url = `http://localhost:5000/api/export/leads/csv`;
        if (vendedorId) url += `?vendedor_id=${vendedorId}`;
      }

      const response = await fetch(url, {
        method: 'GET',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Erro ao exportar');

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      
      // Nome do arquivo baseado no tipo
      const timestamp = new Date().toISOString().split('T')[0];
      if (type === 'metrics-pdf') {
        a.download = `metricas_${timestamp}.pdf`;
      } else if (type === 'leads-excel') {
        a.download = `leads_${timestamp}.xlsx`;
      } else {
        a.download = `leads_${timestamp}.csv`;
      }
      
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      alert('✅ Exportação concluída com sucesso!');
    } catch (error) {
      console.error('Erro ao exportar:', error);
      alert('❌ Erro ao exportar. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="export-buttons">
      <div className="export-header">
        <Download size={20} />
        <span>Exportar Dados</span>
      </div>
      
      <div className="export-grid">
        {(currentUser?.role === 'admin' || currentUser?.role === 'gestor') && (
          <button 
            className="export-btn pdf"
            onClick={() => handleExport('metrics-pdf')}
            disabled={loading}
          >
            <FileText size={18} />
            <div className="export-btn-content">
              <span className="export-btn-label">Métricas PDF</span>
              <span className="export-btn-desc">Relatório completo</span>
            </div>
          </button>
        )}

        <button 
          className="export-btn excel"
          onClick={() => handleExport('leads-excel')}
          disabled={loading}
        >
          <Table size={18} />
          <div className="export-btn-content">
            <span className="export-btn-label">Leads Excel</span>
            <span className="export-btn-desc">Planilha completa</span>
          </div>
        </button>

        <button 
          className="export-btn csv"
          onClick={() => handleExport('leads-csv')}
          disabled={loading}
        >
          <File size={18} />
          <div className="export-btn-content">
            <span className="export-btn-label">Leads CSV</span>
            <span className="export-btn-desc">Arquivo de texto</span>
          </div>
        </button>
      </div>

      {loading && (
        <div className="export-loading">
          <div className="spinner"></div>
          <span>Gerando arquivo...</span>
        </div>
      )}
    </div>
  );
}