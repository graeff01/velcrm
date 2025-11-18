import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2 } from 'lucide-react';
import api from '../api';
import '../styles/components/UserManagement.css';
import { toast } from './Toast';

export default function UserManagement({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    name: '',
    role: 'vendedor'
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await api.getUsers({ noCache: true });
      setUsers(data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
      toast.error("❌ Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;

    setSaving(true);
    try {
      if (editingUser) {
        await api.updateUser(editingUser.id, formData);
        toast.success("Usuário atualizado!");
      } else {
        const res = await api.createUser(formData);
        if (res?.success) {
          toast.success("Usuário criado com sucesso!");
        } else {
          toast.error("Erro ao criar usuário");
        }
      }

      setShowModal(false);
      setEditingUser(null);
      setFormData({ username: '', password: '', name: '', role: 'vendedor' });

      setTimeout(() => loadUsers(), 300);

    } catch (error) {
      console.log(error);
      toast.error("Erro ao salvar usuário");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      name: user.name,
      username: user.username,
      role: user.role,
      password: ''
    });
    setShowModal(true);
  };

  const handleDelete = async (userId) => {
    if (!window.confirm("Desativar este usuário?")) return;

    try {
      await api.deleteUser(userId);
      toast.success("Usuário desativado");
      loadUsers();
    } catch {
      toast.error("Erro ao desativar usuário");
    }
  };

  const getRoleBadgeClass = (role) => ({
    admin: "role-admin",
    gestor: "role-gestor",
    vendedor: "role-vendedor"
  }[role] || "role-vendedor");

  const getRoleLabel = (role) => ({
    admin: "ADMIN",
    gestor: "GESTOR",
    vendedor: "VENDEDOR"
  }[role] || role.toUpperCase());

  return (
    <div className="user-management">

      {/* HEADER */}
      <div className="user-management-header">
        <h1>Gestão de Usuários</h1>

        {currentUser.role === 'admin' && (
          <button 
            className="btn-new-user" 
            onClick={() => {
              setShowModal(true);
              setEditingUser(null);
              setFormData({ username: '', password: '', name: '', role: 'vendedor' });
            }}
          >
            <Plus size={18}/> Novo Usuário
          </button>
        )}
      </div>

      {/* LOADING */}
      {loading && (
        <div className="users-loading">
          <div className="spinner"></div>
          <p>Carregando usuários...</p>
        </div>
      )}

      {/* EMPTY */}
      {!loading && users.length === 0 && (
        <p className="users-empty-state">Nenhum usuário cadastrado</p>
      )}

      {/* TABELA */}
      {!loading && users.length > 0 && (
        <div className="users-table-container">

          <div className="users-table-header">
            <div>Nome</div>
            <div>Usuário</div>
            <div>Função</div>
            <div>Status</div>
            <div>Ações</div>
          </div>

          <div className="users-table-body">
            {users.map(user => (
              <div key={user.id} className="user-row">

                <div className="user-name">{user.name}</div>

                <div className="user-username">{user.username}</div>

                <div className={`user-role ${getRoleBadgeClass(user.role)}`}>
                  {getRoleLabel(user.role)}
                </div>

                <div className="user-status">
                  {user.active ? "✅" : "❌"}
                </div>

                {currentUser.role === 'admin' && (
                  <div className="user-actions">
                    <button className="btn-action btn-edit" onClick={() => handleEdit(user)}>
                      <Edit size={18}/>
                    </button>
                    <button className="btn-action btn-delete" onClick={() => handleDelete(user.id)}>
                      <Trash2 size={18}/>
                    </button>
                  </div>
                )}

              </div>
            ))}
          </div>

        </div>
      )}

      {/* MODAL */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => !saving && setShowModal(false)}>
          <div className="modal user-modal" onClick={(e) => e.stopPropagation()}>

            <div className="modal-header">
              <h3>{editingUser ? "Editar Usuário" : "Novo Usuário"}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>

            <form onSubmit={handleSubmit} className="modal-form">

              <div className="form-group">
                <label>Nome Completo</label>
                <input 
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              {!editingUser && (
                <>
                  <div className="form-group">
                    <label>Usuário (login)</label>
                    <input 
                      required
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label>Senha</label>
                    <input 
                      type="password"
                      required
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    />
                  </div>
                </>
              )}

              <div className="form-group">
                <label>Perfil</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="vendedor">Vendedor</option>
                  <option value="gestor">Gestor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="modal-actions">
                <button disabled={saving} type="submit" className="btn btn-primary">
                  {saving ? "Salvando..." : editingUser ? "Atualizar" : "Criar"}
                </button>
                <button disabled={saving} type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
