import React, { createContext, useContext } from 'react';

const PermissionsContext = createContext();

export const usePermissions = () => {
  const context = useContext(PermissionsContext);
  if (!context) {
    throw new Error('usePermissions deve ser usado dentro de PermissionsProvider');
  }
  return context;
};

export const PermissionsProvider = ({ children, currentUser }) => {
  // Verifica se usuário pode acessar lead específico
  const canAccessLead = (lead) => {
    if (!currentUser) return false;
    
    const { role, id } = currentUser;
    
    // Admin e Gestor podem acessar tudo
    if (role === 'admin' || role === 'gestor') {
      return true;
    }
    
    // Vendedor só pode acessar seus próprios leads
    if (role === 'vendedor') {
      return lead.assigned_to === id;
    }
    
    return false;
  };

  // Verifica se pode modificar lead
  const canModifyLead = (lead) => {
    if (!currentUser) return false;
    
    const { role, id } = currentUser;
    
    // Admin pode modificar tudo
    if (role === 'admin') {
      return true;
    }
    
    // Gestor pode modificar tudo
    if (role === 'gestor') {
      return true;
    }
    
    // Vendedor só pode modificar seus leads
    if (role === 'vendedor') {
      return lead.assigned_to === id;
    }
    
    return false;
  };

  // Verifica se pode redistribuir leads
  const canReassignLeads = () => {
    if (!currentUser) return false;
    return currentUser.role === 'admin' || currentUser.role === 'gestor';
  };

  // Verifica se pode ver todos os leads
  const canViewAllLeads = () => {
    if (!currentUser) return false;
    return currentUser.role === 'admin' || currentUser.role === 'gestor';
  };

  // Verifica se pode gerenciar usuários
  const canManageUsers = () => {
    if (!currentUser) return false;
    return currentUser.role === 'admin';
  };

  // Verifica se pode ver métricas completas
  const canViewFullMetrics = () => {
    if (!currentUser) return false;
    return currentUser.role === 'admin' || currentUser.role === 'gestor';
  };

  // Verifica se é vendedor
  const isVendedor = () => {
    if (!currentUser) return false;
    return currentUser.role === 'vendedor';
  };

  // Verifica se é gestor
  const isGestor = () => {
    if (!currentUser) return false;
    return currentUser.role === 'gestor';
  };

  // Verifica se é admin
  const isAdmin = () => {
    if (!currentUser) return false;
    return currentUser.role === 'admin';
  };

  const permissions = {
    canAccessLead,
    canModifyLead,
    canReassignLeads,
    canViewAllLeads,
    canManageUsers,
    canViewFullMetrics,
    isVendedor,
    isGestor,
    isAdmin,
    currentUser
  };

  return (
    <PermissionsContext.Provider value={permissions}>
      {children}
    </PermissionsContext.Provider>
  );
};