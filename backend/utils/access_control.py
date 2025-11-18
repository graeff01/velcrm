"""
Utilities para controle de acesso e ownership
Verifica se usuário tem permissão para acessar recursos específicos
"""
from flask import g, jsonify

class AccessControl:
    """Controla acesso a recursos baseado em role e ownership"""
    
    @staticmethod
    def can_access_lead(lead, user=None):
        """
        Verifica se usuário pode acessar um lead específico
        
        Args:
            lead: Objeto Lead do banco
            user: Objeto User (opcional, usa g.current_user se não fornecido)
        
        Returns:
            bool: True se pode acessar, False caso contrário
        """
        if user is None:
            user = g.current_user
        
        # Admin e Gestor podem acessar tudo
        if user.role in ['admin', 'gestor']:
            return True
        
        # Vendedor só pode acessar leads atribuídos a ele
        if user.role == 'vendedor':
            return lead.assigned_to == user.id
        
        return False
    
    @staticmethod
    def can_modify_lead(lead, user=None):
        """
        Verifica se usuário pode modificar um lead
        
        Args:
            lead: Objeto Lead do banco
            user: Objeto User (opcional, usa g.current_user se não fornecido)
        
        Returns:
            bool: True se pode modificar, False caso contrário
        """
        if user is None:
            user = g.current_user
        
        # Admin pode modificar tudo
        if user.role == 'admin':
            return True
        
        # Gestor pode modificar leads da sua equipe
        if user.role == 'gestor':
            return True
        
        # Vendedor só pode modificar seus próprios leads
        if user.role == 'vendedor':
            return lead.assigned_to == user.id
        
        return False
    
    @staticmethod
    def can_reassign_lead(user=None):
        """
        Verifica se usuário pode reatribuir leads
        Apenas Admin e Gestor podem redistribuir
        
        Args:
            user: Objeto User (opcional, usa g.current_user se não fornecido)
        
        Returns:
            bool: True se pode reatribuir, False caso contrário
        """
        if user is None:
            user = g.current_user
        
        return user.role in ['admin', 'gestor']
    
    @staticmethod
    def filter_leads_by_access(query, user=None):
        """
        Filtra query de leads baseado no acesso do usuário
        
        Args:
            query: SQLAlchemy query de Leads
            user: Objeto User (opcional, usa g.current_user se não fornecido)
        
        Returns:
            Query filtrada
        """
        if user is None:
            user = g.current_user
        
        # Admin e Gestor veem tudo
        if user.role in ['admin', 'gestor']:
            return query
        
        # Vendedor vê apenas seus leads
        if user.role == 'vendedor':
            return query.filter_by(assigned_to=user.id)
        
        return query
    
    @staticmethod
    def get_accessible_users(user=None):
        """
        Retorna lista de usuários que o current_user pode ver/gerenciar
        
        Args:
            user: Objeto User (opcional, usa g.current_user se não fornecido)
        
        Returns:
            Query de usuários acessíveis
        """
        from models.user import User
        
        if user is None:
            user = g.current_user
        
        # Admin vê todos
        if user.role == 'admin':
            return User.query.filter_by(is_active=True)
        
        # Gestor vê vendedores + outros gestores
        if user.role == 'gestor':
            return User.query.filter(
                User.is_active == True,
                User.role.in_(['vendedor', 'gestor'])
            )
        
        # Vendedor vê apenas a si mesmo
        if user.role == 'vendedor':
            return User.query.filter_by(id=user.id)
        
        return User.query.filter_by(id=-1)  # Retorna vazio


def require_lead_access(f):
    """
    Decorator para verificar acesso a lead específico
    Espera que lead_id seja passado como parâmetro da rota
    
    Usage:
        @require_lead_access
        def update_lead(lead_id):
            # Se chegou aqui, tem acesso
            # Lead estará em g.current_lead
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(lead_id, *args, **kwargs):
        from models.lead import Lead
        
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({'error': 'Lead não encontrado'}), 404
        
        if not AccessControl.can_access_lead(lead):
            return jsonify({
                'error': 'Acesso negado',
                'message': 'Você não tem permissão para acessar este lead'
            }), 403
        
        # Disponibiliza lead na request
        g.current_lead = lead
        return f(lead_id, *args, **kwargs)
    
    return decorated_function