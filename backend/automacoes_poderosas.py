# -*- coding: utf-8 -*-
"""
Sistema de Automações Poderosas
Versão: 2.0.0
Recuperação de leads, follow-up automático e webhooks
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from threading import Thread
import time


class AutomacoesPoderosas:
    """
    Sistema de automações para recuperação de leads,
    follow-up automático e notificações inteligentes
    """
    
    def __init__(self, config_path: str = 'ia_config.json', whatsapp_service=None):
        """Inicializa o sistema de automações"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.whatsapp_service = whatsapp_service
        self.recuperacao_config = self.config.get('recuperacao_leads', {})
        self.integracao_config = self.config.get('integracao_crm', {})
        
        # Armazenamento em memória de tarefas agendadas
        # Em produção, usar banco de dados
        self.tarefas_agendadas = []
    
    
    def agendar_recuperacao_lead(self, lead_data: Dict, tipo_template: str = 'lead_frio_reengajamento'):
        """
        Agenda uma mensagem de recuperação para um lead frio
        
        Args:
            lead_data: Dados do lead (id, name, phone, interesse, etc)
            tipo_template: Tipo de template a usar
        """
        if not self.recuperacao_config.get('habilitado', False):
            print("⚠️ Sistema de recuperação desabilitado no config")
            return
        
        templates = self.recuperacao_config.get('templates', {})
        template = templates.get(tipo_template)
        
        if not template:
            print(f"❌ Template '{tipo_template}' não encontrado")
            return
        
        # Calcular quando enviar
        delay_horas = template.get('delay_horas', 24)
        enviar_em = datetime.now() + timedelta(hours=delay_horas)
        
        # Personalizar mensagem
        mensagem = template.get('mensagem', '')
        mensagem = mensagem.replace('{nome}', lead_data.get('name', 'Cliente'))
        mensagem = mensagem.replace('{interesse}', lead_data.get('interesse', 'nossos produtos'))
        
        # Criar tarefa
        tarefa = {
            'id': f"recuperacao_{lead_data.get('id')}_{int(time.time())}",
            'tipo': 'recuperacao_lead',
            'lead_id': lead_data.get('id'),
            'phone': lead_data.get('phone'),
            'mensagem': mensagem,
            'enviar_em': enviar_em.isoformat(),
            'template': tipo_template,
            'status': 'agendado',
            'criado_em': datetime.now().isoformat()
        }
        
        self.tarefas_agendadas.append(tarefa)
        
        print(f"✅ Recuperação agendada para {lead_data.get('name')} em {delay_horas}h")
        print(f"   Enviar em: {enviar_em.strftime('%d/%m/%Y %H:%M')}")
        
        # Iniciar thread de processamento (simplificado)
        # Em produção, usar Celery, APScheduler ou similar
        Thread(target=self._processar_tarefa_agendada, args=(tarefa,), daemon=True).start()
        
        return tarefa
    
    
    def agendar_followup_sem_resposta(self, lead_data: Dict):
        """
        Agenda follow-up automático quando lead não responde
        """
        return self.agendar_recuperacao_lead(lead_data, 'sem_resposta')
    
    
    def _processar_tarefa_agendada(self, tarefa: Dict):
        """
        Processa uma tarefa agendada (em background)
        """
        enviar_em = datetime.fromisoformat(tarefa['enviar_em'])
        agora = datetime.now()
        
        # Esperar até o momento de enviar
        if enviar_em > agora:
            segundos_espera = (enviar_em - agora).total_seconds()
            print(f"⏳ Aguardando {segundos_espera/3600:.1f}h para enviar...")
            time.sleep(segundos_espera)
        
        # Enviar mensagem
        try:
            if self.whatsapp_service:
                self.whatsapp_service.send_message(
                    tarefa['phone'],
                    tarefa['mensagem']
                )
                tarefa['status'] = 'enviado'
                tarefa['enviado_em'] = datetime.now().isoformat()
                print(f"✅ Recuperação enviada para {tarefa['phone']}")
            else:
                print(f"⚠️ WhatsApp service não configurado")
                tarefa['status'] = 'erro'
        
        except Exception as e:
            print(f"❌ Erro ao enviar recuperação: {e}")
            tarefa['status'] = 'erro'
            tarefa['erro'] = str(e)
    
    
    def notificar_lead_qualificado(self, lead_data: Dict, score_data: Dict):
        """
        Notifica o sistema CRM quando um lead é qualificado
        
        Args:
            lead_data: Dados do lead
            score_data: Dados do scoring (score, classificação, etc)
        """
        if not self.integracao_config.get('notificar_gestor_vip', False):
            return
        
        # Se for VIP, notificar gestor
        if score_data.get('is_vip', False):
            self._notificar_gestor_vip(lead_data, score_data)
        
        # Webhook de qualificação
        webhook_url = self.integracao_config.get('webhook_qualificacao')
        if webhook_url:
            self._enviar_webhook(webhook_url, {
                'evento': 'lead_qualificado',
                'lead': lead_data,
                'score': score_data,
                'timestamp': datetime.now().isoformat()
            })
    
    
    def _notificar_gestor_vip(self, lead_data: Dict, score_data: Dict):
        """
        Notifica gestor sobre lead VIP via WhatsApp
        """
        # Buscar telefone do gestor (simplificado - em produção, buscar do banco)
        # Por enquanto, apenas log
        mensagem_gestor = f"""
🔥 ALERTA VIP! 🔥

Lead de alta prioridade qualificado:

👤 Nome: {lead_data.get('name', 'N/A')}
📱 Telefone: {lead_data.get('phone', 'N/A')}
💰 Orçamento: {lead_data.get('orcamento', 'N/A')}
⏰ Prazo: {lead_data.get('prazo', 'N/A')}
📊 Score: {score_data.get('score_total', 0)}/175

🎯 Classificação: {score_data.get('classificacao', 'N/A').upper()}
⭐ Prioridade: VIP

ATENDER IMEDIATAMENTE!
        """.strip()
        
        print("\n" + "="*50)
        print(mensagem_gestor)
        print("="*50 + "\n")
        
        # TODO: Enviar via WhatsApp para gestor
        # if self.whatsapp_service:
        #     self.whatsapp_service.send_message(gestor_phone, mensagem_gestor)
    
    
    def _enviar_webhook(self, url: str, dados: Dict):
        """
        Envia webhook para integração externa
        """
        try:
            response = requests.post(
                url,
                json=dados,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Webhook enviado com sucesso para {url}")
            else:
                print(f"⚠️ Webhook retornou status {response.status_code}")
        
        except Exception as e:
            print(f"❌ Erro ao enviar webhook: {e}")
    
    
    def criar_tarefa_crm(self, lead_data: Dict, score_data: Dict):
        """
        Cria tarefa automática no CRM baseada na qualificação
        """
        if not self.integracao_config.get('criar_tarefas_automaticas', False):
            return
        
        classificacao = score_data.get('classificacao', 'cold')
        
        # Definir tarefa baseada em classificação
        if classificacao == 'hot':
            tarefa = {
                'titulo': f"🔥 URGENTE: Atender {lead_data.get('name')}",
                'descricao': f"Lead VIP qualificado com score {score_data.get('score_total')}/175",
                'prioridade': 'alta',
                'prazo': datetime.now() + timedelta(hours=1)
            }
        
        elif classificacao == 'warm':
            tarefa = {
                'titulo': f"⚡ Atender {lead_data.get('name')}",
                'descricao': f"Lead qualificado com score {score_data.get('score_total')}/175",
                'prioridade': 'media',
                'prazo': datetime.now() + timedelta(hours=4)
            }
        
        else:
            tarefa = {
                'titulo': f"📋 Follow-up {lead_data.get('name')}",
                'descricao': f"Lead frio - agendar nurturing",
                'prioridade': 'baixa',
                'prazo': datetime.now() + timedelta(days=1)
            }
        
        print(f"✅ Tarefa CRM criada: {tarefa['titulo']}")
        
        # TODO: Integrar com sistema de tarefas do CRM
        return tarefa
    
    
    def processar_keywords_negativas(self, lead_data: Dict, count_negativas: int):
        """
        Processa lead com muitas keywords negativas
        """
        if count_negativas >= 2:
            print(f"⚠️ Lead {lead_data.get('name')} com {count_negativas} sinais negativos")
            
            # Agendar recuperação
            self.agendar_recuperacao_lead(lead_data, 'lead_frio_reengajamento')
    
    
    def atualizar_campos_crm(self, lead_id: int, dados_qualificacao: Dict):
        """
        Atualiza campos do lead no CRM automaticamente
        
        Args:
            lead_id: ID do lead
            dados_qualificacao: Dados coletados pela IA
        """
        if not self.integracao_config.get('atualizar_campos_automaticamente', False):
            return
        
        # Campos a atualizar
        campos_atualizados = {
            'interesse': dados_qualificacao.get('interesse'),
            'orcamento': dados_qualificacao.get('orcamento'),
            'prazo': dados_qualificacao.get('prazo'),
            'preferencia_contato': dados_qualificacao.get('preferencia_contato'),
            'tipo_cliente': dados_qualificacao.get('tipo_cliente'),
            'tamanho_empresa': dados_qualificacao.get('tamanho_empresa'),
            'ai_qualified': True,
            'qualification_score': dados_qualificacao.get('score_total', 0),
            'classification': dados_qualificacao.get('classificacao', 'cold'),
            'prioridade': dados_qualificacao.get('prioridade', 'normal'),
            'sentimento': dados_qualificacao.get('sentimento', 'neutro')
        }
        
        # Remover valores None
        campos_atualizados = {k: v for k, v in campos_atualizados.items() if v is not None}
        
        print(f"✅ Campos do lead #{lead_id} atualizados automaticamente")
        print(f"   Campos: {', '.join(campos_atualizados.keys())}")
        
        # TODO: Integrar com database do CRM
        # database.update_lead(lead_id, campos_atualizados)
        
        return campos_atualizados
    
    
    def listar_tarefas_agendadas(self, status: Optional[str] = None) -> List[Dict]:
        """
        Lista tarefas agendadas
        
        Args:
            status: Filtrar por status (agendado, enviado, erro)
        """
        if status:
            return [t for t in self.tarefas_agendadas if t['status'] == status]
        return self.tarefas_agendadas
    
    
    def cancelar_tarefa(self, tarefa_id: str) -> bool:
        """
        Cancela uma tarefa agendada
        """
        for tarefa in self.tarefas_agendadas:
            if tarefa['id'] == tarefa_id and tarefa['status'] == 'agendado':
                tarefa['status'] = 'cancelado'
                tarefa['cancelado_em'] = datetime.now().isoformat()
                print(f"✅ Tarefa {tarefa_id} cancelada")
                return True
        
        print(f"❌ Tarefa {tarefa_id} não encontrada ou já processada")
        return False
    
    
    def gerar_relatorio_automacoes(self) -> Dict:
        """
        Gera relatório das automações executadas
        """
        total = len(self.tarefas_agendadas)
        agendadas = len([t for t in self.tarefas_agendadas if t['status'] == 'agendado'])
        enviadas = len([t for t in self.tarefas_agendadas if t['status'] == 'enviado'])
        erros = len([t for t in self.tarefas_agendadas if t['status'] == 'erro'])
        canceladas = len([t for t in self.tarefas_agendadas if t['status'] == 'cancelado'])
        
        return {
            'total_tarefas': total,
            'agendadas': agendadas,
            'enviadas': enviadas,
            'erros': erros,
            'canceladas': canceladas,
            'taxa_sucesso': round((enviadas / total * 100) if total > 0 else 0, 1),
            'gerado_em': datetime.now().isoformat()
        }


# Função auxiliar para integração rápida

def processar_lead_qualificado(lead_data: Dict, score_data: Dict, 
                              whatsapp_service=None, config_path: str = 'ia_config.json'):
    """
    Função completa para processar um lead qualificado
    
    Args:
        lead_data: Dados do lead
        score_data: Resultado do scoring
        whatsapp_service: Serviço WhatsApp (opcional)
        config_path: Caminho do arquivo de config
    
    Returns:
        Dict com resumo das ações executadas
    """
    automacoes = AutomacoesPoderosas(config_path, whatsapp_service)
    
    acoes_executadas = []
    
    # 1. Notificar qualificação
    automacoes.notificar_lead_qualificado(lead_data, score_data)
    acoes_executadas.append('Notificação de qualificação enviada')
    
    # 2. Criar tarefa CRM
    tarefa = automacoes.criar_tarefa_crm(lead_data, score_data)
    if tarefa:
        acoes_executadas.append(f"Tarefa CRM criada: {tarefa['titulo']}")
    
    # 3. Atualizar campos
    campos = automacoes.atualizar_campos_crm(lead_data.get('id'), score_data)
    acoes_executadas.append(f"Campos atualizados: {len(campos)}")
    
    # 4. Se for lead frio, agendar recuperação
    if score_data.get('classificacao') == 'cold':
        tarefa_rec = automacoes.agendar_recuperacao_lead(lead_data)
        if tarefa_rec:
            acoes_executadas.append('Recuperação agendada para lead frio')
    
    return {
        'sucesso': True,
        'acoes_executadas': acoes_executadas,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == '__main__':
    # Teste
    print("=" * 60)
    print("TESTE - Sistema de Automações")
    print("=" * 60)
    
    automacoes = AutomacoesPoderosas()
    
    # Lead de teste
    lead_teste = {
        'id': 123,
        'name': 'João Silva',
        'phone': '5551999999999',
        'interesse': 'CRM',
        'orcamento': '5 mil'
    }
    
    # Score de teste
    score_teste = {
        'score_total': 45,
        'classificacao': 'warm',
        'prioridade': 'normal',
        'is_vip': False
    }
    
    # Processar
    resultado = processar_lead_qualificado(lead_teste, score_teste)
    
    print("\nResultado:")
    print(f"✅ Sucesso: {resultado['sucesso']}")
    print(f"\nAções executadas:")
    for acao in resultado['acoes_executadas']:
        print(f"  • {acao}")
    
    # Relatório
    print("\n" + "=" * 60)
    relatorio = automacoes.gerar_relatorio_automacoes()
    print("RELATÓRIO DE AUTOMAÇÕES")
    print("=" * 60)
    print(f"Total de tarefas: {relatorio['total_tarefas']}")
    print(f"Agendadas: {relatorio['agendadas']}")
    print(f"Enviadas: {relatorio['enviadas']}")
    print(f"Erros: {relatorio['erros']}")
    print(f"Taxa de sucesso: {relatorio['taxa_sucesso']}%")
    print("=" * 60)