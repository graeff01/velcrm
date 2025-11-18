import { useEffect, useState } from "react";
import api from "../api";
import { FileText, PlusCircle, Loader2 } from "lucide-react";
import "../styles/components/timeline.css";

export default function LeadTimeline({ leadId }) {
  const [notes, setNotes] = useState([]);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [addingNote, setAddingNote] = useState(false);

  // =============================
  // 🔁 CARREGAR SOMENTE NOTAS
  // =============================
  useEffect(() => {
    if (!leadId) return;
    loadNotes();
  }, [leadId]);

  const loadNotes = async () => {
    try {
      setLoading(true);
      const data = await api.getLeadLogs(leadId);
      const onlyNotes = data.filter((log) =>
        log.action.toLowerCase().includes("nota")
      );
      setNotes(onlyNotes.reverse()); // mais recentes no topo
    } catch (error) {
      console.error("Erro ao carregar notas:", error);
    } finally {
      setLoading(false);
    }
  };

  // =============================
  // 📝 ADICIONAR NOTA
  // =============================
  const handleAddNote = async () => {
    if (!note.trim()) return;
    try {
      setAddingNote(true);
      await api.addNote(leadId, note);
      setNote("");
      await loadNotes();
    } catch (error) {
      console.error("Erro ao adicionar nota:", error);
    } finally {
      setAddingNote(false);
    }
  };

  // =============================
  // 🧱 RENDER
  // =============================
  return (
    <div className="lead-notes-wrapper">
      {/* Formulário */}
      <div className="add-note-box">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Adicionar nota interna..."
          className="note-input"
        />
        <button
          className="add-note-btn"
          onClick={handleAddNote}
          disabled={!note.trim() || addingNote}
        >
          {addingNote ? (
            <Loader2 size={16} className="spin" />
          ) : (
            <PlusCircle size={16} />
          )}
          {addingNote ? " Salvando..." : " Adicionar Nota"}
        </button>
      </div>

      {/* Lista de notas */}
      {loading ? (
        <div className="note-loading">Carregando notas...</div>
      ) : notes.length === 0 ? (
        <div className="note-empty">Nenhuma nota adicionada ainda.</div>
      ) : (
        <div className="notes-list">
          {notes.map((log, i) => (
            <div key={i} className="note-card">
              <div className="note-icon">
                <FileText size={18} color="#8b5cf6" />
              </div>
              <div className="note-content">
                <div className="note-header">
                  <strong>{log.user_name || "Usuário"}</strong>
                  <span>
                    {new Date(log.timestamp).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <p>{log.details}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}