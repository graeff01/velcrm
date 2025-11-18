# -*- coding: utf-8 -*-
"""
🤖 IA ASSISTANT - Motor de Qualificação de Leads
VERSÃO 2.1 - CORRIGIDO E INTEGRADO
Compatível com ia_config.json v2.0.0
"""

from triagem_inteligente import TriagemInteligente, classificar_lead_simples
from automacoes_poderosas import AutomacoesPoderosas, processar_lead_qualificado
import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
import re


class IAAssistant:
    """
    Motor principal de qualificação de leads com IA
    Integra: OpenAI + Triagem Inteligente + Automações
    """
    
    def __init__(self, database, whatsapp_service=None, config_path="ia_config.json"):
        """
        Inicializa o assistente de IA

        Args:
            database: Instância do Database
            whatsapp_service: Instância do WhatsAppService (opcional)
            config_path: Caminho para arquivo de configuração
        """
        self.db = database
        self.whatsapp = whatsapp_service
        self.config_path = config_path
        self.config = self._carregar_config(config_path)

        # ✅ CORRIGIDO: Inicializar OpenAI (se API key disponível)
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_habilitada = bool(api_key)

        if self.openai_habilitada:
            self.client = OpenAI(api_key=api_key)
            print("✅ OpenAI inicializada com sucesso")
        else:
            self.client = None
            print("⚠️ OPENAI_API_KEY não encontrada - usando fallback sem IA")

        # ✅ CORRIGIDO: Inicializar Sistema de Triagem
        # Agora recebe apenas config_path
        try:
            self.triagem = TriagemInteligente(config_path=self.config_path)
            print("✅ Sistema de Triagem Inteligente inicializado")
        except Exception as e:
            print(f"❌ Erro ao inicializar Triagem: {e}")
            self.triagem = None
        
        # ✅ CORRIGIDO: Inicializar Automações
        # Agora recebe config_path e whatsapp_service
        try:
            if whatsapp_service:
                self.automacoes = AutomacoesPoderosas(
                    config_path=self.config_path,
                    whatsapp_service=whatsapp_service
                )
                print("✅ Sistema de Automações inicializado")
            else:
                self.automacoes = None
                print("⚠️ Automações desabilitadas (WhatsApp não disponível)")
        except Exception as e:
            print(f"❌ Erro ao inicializar Automações: {e}")
            self.automacoes = None

    def _carregar_config(self, path):
        """Carrega configuração do JSON"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), path)
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Configuração carregada: {config_file}")
                return config
        except Exception as e:
            print(f"❌ Erro ao carregar config: {e}")
            return self._config_padrao()

    def _config_padrao(self):
        """Config mínima de fallback"""
        return {
            "ia_habilitada": False,
            "fallback_sem_api": {
                "habilitado": True,
                "mensagem": "Obrigado! Um atendente responderá em breve."
            }
        }

    def processar_mensagem(self, lead_id, mensagem_lead):
        """
        Processa mensagem do lead com Sistema de Triagem integrado
        
        Args:
            lead_id: ID do lead
            mensagem_lead: Mensagem enviada pelo lead
            
        Returns:
            str: Resposta da IA (ou None se não deve responder)
        """
        try:
            # ✅ 1. Verificar se IA está habilitada
            if not self.config.get("ia_habilitada", False):
                return None

            lead = self.db.get_lead(lead_id)
            if not lead:
                print(f"❌ Lead {lead_id} não encontrado")
                return None

            # ✅ 2. Obter histórico de mensagens
            historico = self.db.get_messages_by_lead(lead_id)
            
            # ✅ 3. Verificar se lead quer falar com humano
            if self._detectar_pedido_humano(mensagem_lead):
                self._escalar_para_humano(lead_id)
                return self.config.get("mensagem_escalar",
                    "Vou conectar você com um atendente agora!")

            # ✅ 4. Verificar se já está qualificado ou em atendimento
            if lead.get('ai_qualified', False) or lead['status'] in ['em_atendimento', 'ganho', 'perdido']:
                return None

            # ✅ 5. Se é primeira mensagem, enviar saudação
            if len(historico) == 1:
                saudacao = self._gerar_saudacao()
                
                self.db.add_message(
                    lead_id=lead_id,
                    sender_type='ia',
                    sender_name='Assistente IA',
                    content=saudacao
                )
                
                return saudacao

            # ✅ 6. Verificar timeout de qualificação
            if self._timeout_expirado(lead_id):
                self._escalar_para_humano(lead_id)
                return "Vou te conectar com um atendente para continuar. 👨‍💼"

            # ✅ 7. Verificar quantas perguntas já foram respondidas
            respostas_salvas = self.db.get_lead_qualificacao_respostas(lead_id)
            perguntas_obrigatorias = [
                p for p in self.config["perguntas_qualificacao"] 
                if p.get('obrigatoria', False)
            ]
            
            # ✅ 8. Se respondeu todas as obrigatórias, QUALIFICAR COM SISTEMA COMPLETO
            if self._todas_obrigatorias_respondidas(lead_id):
                return self._finalizar_qualificacao(lead_id, historico)

            # ✅ 9. Gerar próxima pergunta com IA (ou sequencial se sem OpenAI)
            if self.openai_habilitada and self.client:
                resposta_ia = self._gerar_resposta_ia(lead_id, mensagem_lead, historico)
            else:
                resposta_ia = self._proxima_pergunta_sequencial(lead_id)
            
            if resposta_ia:
                self.db.add_message(
                    lead_id=lead_id,
                    sender_type='ia',
                    sender_name='Assistente IA',
                    content=resposta_ia
                )
                
                self.db.add_lead_log(
                    lead_id,
                    'ia_respondeu',
                    'IA Assistant',
                    f'IA enviou: {resposta_ia[:50]}...'
                )
            
            return resposta_ia

        except Exception as e:
            print(f"❌ Erro ao processar mensagem IA: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _finalizar_qualificacao(self, lead_id, historico):
        """
        ✨ NOVO: Finaliza qualificação usando Sistema de Triagem Completo
        Score 0-180, classificação hot/warm/cold, automações
        """
        try:
            lead = self.db.get_lead(lead_id)
            
            # ✅ 1. Obter respostas coletadas
            respostas_db = self.db.get_lead_qualificacao_respostas(lead_id)
            
            # ✅ 2. Converter para formato esperado pela Triagem
            respostas_dict = {}
            for resp in respostas_db:
                pergunta_id = resp['pergunta_id']
                
                # Buscar campo_lead da pergunta
                pergunta_config = next(
                    (p for p in self.config['perguntas_qualificacao'] if p['id'] == pergunta_id),
                    None
                )
                
                if pergunta_config:
                    campo_lead = pergunta_config.get('campo_lead', pergunta_id)
                    respostas_dict[campo_lead] = resp['resposta']
            
            # ✅ 3. CALCULAR SCORE COMPLETO (0-180) COM TRIAGEM INTELIGENTE
            if self.triagem:
                score_data = self.triagem.calcular_score_completo(
                    respostas=respostas_dict,
                    historico_mensagens=historico
                )
                
                print("\n" + "="*60)
                print("🎯 QUALIFICAÇÃO COMPLETA")
                print("="*60)
                print(f"Score: {score_data['score_total']}/175")
                print(f"Classificação: {score_data['classificacao'].upper()}")
                print(f"Prioridade: {score_data['prioridade'].upper()}")
                print(f"VIP: {'SIM ⭐' if score_data['is_vip'] else 'NÃO'}")
                print(f"Sentimento: {score_data['sentimento']}")
                print("="*60 + "\n")
                
            else:
                # Fallback se triagem não disponível
                score_data = {
                    'score_total': 50,
                    'classificacao': 'warm',
                    'prioridade': 'normal',
                    'is_vip': False,
                    'sentimento': 'neutro',
                    'qualificado': True
                }
            
            # ✅ 4. ATUALIZAR LEAD NO BANCO COM TODOS OS DADOS
            self._atualizar_lead_qualificado(lead_id, respostas_dict, score_data)
            
            # ✅ 5. PROCESSAR AUTOMAÇÕES (notificações, follow-up, etc)
            if self.automacoes:
                lead_data_completo = {
                    'id': lead_id,
                    'name': lead.get('name'),
                    'phone': lead.get('phone'),
                    **respostas_dict
                }
                
                processar_lead_qualificado(
                    lead_data=lead_data_completo,
                    score_data=score_data,
                    whatsapp_service=self.whatsapp,
                    config_path=self.config_path
                )
            
            # ✅ 6. GERAR MENSAGEM FINAL PERSONALIZADA
            mensagem_final = self._gerar_mensagem_qualificacao(
                lead_id, 
                respostas_dict, 
                score_data
            )
            
            self.db.add_message(
                lead_id=lead_id,
                sender_type='ia',
                sender_name='Assistente IA',
                content=mensagem_final
            )
            
            return mensagem_final
        
        except Exception as e:
            print(f"❌ Erro ao finalizar qualificação: {e}")
            import traceback
            traceback.print_exc()
            
            # Mensagem genérica de fallback
            return "Obrigado pelas informações! Um especialista entrará em contato em breve. 😊"

    def _atualizar_lead_qualificado(self, lead_id, respostas_dict, score_data):
        """
        Atualiza lead no banco com todos os dados da qualificação
        """
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            
            # ✅ Atualizar campos do lead
            campos_update = {
                'ai_qualified': True,
                'qualification_score': score_data['score_total'],
                'classification': score_data['classificacao'],
                'prioridade': score_data['prioridade'],
                'sentimento': score_data['sentimento'],
                'status': 'qualificado'
            }
            
            # Adicionar campos das respostas (se existirem na tabela)
            campos_opcionais = ['interesse', 'orcamento', 'prazo', 'preferencia_contato', 
                              'tipo_cliente', 'tamanho_empresa']
            
            for campo in campos_opcionais:
                if campo in respostas_dict:
                    campos_update[campo] = respostas_dict[campo]
            
            # Construir UPDATE dinamicamente
            set_clause = ', '.join([f"{k} = ?" for k in campos_update.keys()])
            values = list(campos_update.values()) + [lead_id]
            
            c.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            
            # Log
            self.db.add_lead_log(
                lead_id,
                'ia_qualificado_completo',
                'Sistema IA',
                f'Lead qualificado - Score: {score_data["score_total"]}/175 - {score_data["classificacao"].upper()}'
            )
            
            print(f"✅ Lead {lead_id} atualizado no banco com qualificação completa")
        
        except Exception as e:
            print(f"❌ Erro ao atualizar lead qualificado: {e}")

    def _gerar_mensagem_qualificacao(self, lead_id, respostas_dict, score_data):
        """
        Gera mensagem final personalizada baseada no score
        """
        lead = self.db.get_lead(lead_id)
        nome = respostas_dict.get('name', lead.get('name', 'Cliente'))
        
        # ✅ Resumo das informações
        resumo_linhas = []
        for campo, valor in respostas_dict.items():
            if campo != 'name':
                label = campo.replace('_', ' ').title()
                resumo_linhas.append(f"• {label}: {valor}")
        
        resumo = "\n".join(resumo_linhas) if resumo_linhas else "Informações coletadas"
        
        # ✅ Mensagem personalizada baseada no score
        mensagens_personalizadas = self.config.get('mensagens_personalizadas', {})
        score_total = score_data['score_total']
        
        if score_total >= 80:
            msg_personalizada = mensagens_personalizadas.get('score_alto', 
                'Vejo que você tem um projeto muito interessante! 🌟')
        elif score_total >= 50:
            msg_personalizada = mensagens_personalizadas.get('score_medio',
                'Temos ótimas soluções que vão te ajudar!')
        else:
            msg_personalizada = mensagens_personalizadas.get('score_baixo',
                'Vamos encontrar a melhor opção para você!')
        
        # ✅ Mensagem completa
        template = self.config.get('mensagem_qualificado', 
            'Perfeito, {nome}! ✅\n\nVou conectar você com um especialista.')
        
        mensagem = template.format(
            nome=nome,
            resumo=resumo,
            mensagem_personalizada=msg_personalizada
        )
        
        return mensagem

    def _detectar_pedido_humano(self, mensagem):
        """Detecta se lead quer falar com humano"""
        mensagem_lower = mensagem.lower()
        keywords = self.config.get("keywords_humano", [])

        for keyword in keywords:
            if keyword.lower() in mensagem_lower:
                return True
        return False

    def _escalar_para_humano(self, lead_id):
        """Marca lead para atendimento humano"""
        self.db.update_lead_status(lead_id, "novo")
        
        # Cancelar automações quando escalar
        if self.automacoes:
            try:
                tarefas = self.automacoes.listar_tarefas_agendadas()
                for tarefa in tarefas:
                    if tarefa.get('lead_id') == lead_id and tarefa.get('status') == 'agendado':
                        self.automacoes.cancelar_tarefa(tarefa['id'])
            except Exception as e:
                print(f"⚠️ Erro ao cancelar automações: {e}")
        
        self.db.add_lead_log(
            lead_id,
            "ia_escalado_humano",
            "IA Assistant",
            "Lead solicitou atendimento humano"
        )
        print(f"🔀 Lead {lead_id} escalado para humano")

    def _timeout_expirado(self, lead_id):
        """Verifica se tempo de qualificação expirou"""
        timeout_min = self.config.get("timeout_qualificacao_minutos", 30)
        lead = self.db.get_lead(lead_id)

        if not lead or not lead.get('created_at'):
            return False

        try:
            created_at = datetime.fromisoformat(lead['created_at'])
            tempo_decorrido = datetime.now() - created_at
            return tempo_decorrido > timedelta(minutes=timeout_min)
        except:
            return False

    def _gerar_saudacao(self):
        """Gera mensagem de saudação inicial"""
        saudacao = self.config.get("saudacao", "Olá! Como posso ajudar?")
        empresa = self.config.get("empresa", "Nossa Empresa")
        return saudacao.format(empresa=empresa)

    def _todas_obrigatorias_respondidas(self, lead_id):
        """Verifica se todas perguntas obrigatórias foram respondidas"""
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        perguntas_config = self.config.get("perguntas_qualificacao", [])

        ids_respondidas = [r['pergunta_id'] for r in respostas]

        for pergunta in perguntas_config:
            if pergunta.get('obrigatoria', False):
                if pergunta['id'] not in ids_respondidas:
                    return False

        return True

    def _proxima_pergunta_sequencial(self, lead_id):
        """Faz próxima pergunta sem usar IA (modo sequencial)"""
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        ids_respondidas = [r['pergunta_id'] for r in respostas]

        perguntas = self.config.get("perguntas_qualificacao", [])

        for pergunta in perguntas:
            # ✅ Verificar se pergunta depende de outra
            depende_de = pergunta.get('depende_de')
            if depende_de:
                # Verificar se a pergunta dependente foi respondida
                resposta_dependente = next(
                    (r for r in respostas if r['pergunta_id'] == depende_de),
                    None
                )
                if not resposta_dependente:
                    continue
            
            if pergunta['id'] not in ids_respondidas:
                self.db.set_lead_proxima_pergunta(lead_id, pergunta['id'])
                return pergunta['pergunta']

        return "Obrigado pelas informações! 😊"

    def _gerar_resposta_ia(self, lead_id, mensagem_lead, historico):
        """Gera resposta usando OpenAI"""
        try:
            contexto = self._construir_contexto_ia(lead_id, historico)

            response = self.client.chat.completions.create(
                model=self.config.get("modelo", "gpt-4o-mini"),
                messages=contexto,
                max_tokens=self.config.get("max_tokens", 150),
                temperature=self.config.get("temperature", 0.7)
            )

            resposta_ia = response.choices[0].message.content.strip()
            
            # ✅ Salvar resposta do lead
            self._extrair_e_salvar_informacao(lead_id, mensagem_lead)

            return resposta_ia

        except Exception as e:
            print(f"❌ Erro ao chamar OpenAI: {e}")
            # Fallback para modo sequencial
            return self._proxima_pergunta_sequencial(lead_id)

    def _construir_contexto_ia(self, lead_id, historico):
        """Constrói contexto para a IA com histórico de mensagens"""
        mensagens = []

        # ✅ Prompt do sistema
        prompt_sistema = self.config.get("prompt_sistema", "Você é um assistente virtual.")

        # ✅ Adicionar informações sobre perguntas pendentes
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        ids_respondidas = [r['pergunta_id'] for r in respostas]
        perguntas_pendentes = [
            p for p in self.config.get("perguntas_qualificacao", [])
            if p['id'] not in ids_respondidas
        ]

        if perguntas_pendentes:
            proxima_pergunta = perguntas_pendentes[0]
            prompt_sistema += f"\n\nPróxima pergunta a fazer: {proxima_pergunta['pergunta']}"
            prompt_sistema += f"\nPerguntas restantes: {len(perguntas_pendentes)}"

        mensagens.append({"role": "system", "content": prompt_sistema})

        # ✅ Adicionar histórico (últimas 10 mensagens)
        for msg in historico[-10:]:
            role = "user" if msg['sender_type'] == 'lead' else "assistant"
            mensagens.append({
                "role": role,
                "content": msg['content']
            })

        return mensagens

    def _extrair_e_salvar_informacao(self, lead_id, mensagem_lead):
        """
        Extrai informação da mensagem e salva no banco
        """
        proxima_pergunta_id = self.db.get_lead_proxima_pergunta(lead_id)

        if proxima_pergunta_id:
            # ✅ Buscar config da pergunta
            pergunta_config = next(
                (p for p in self.config.get("perguntas_qualificacao", []) 
                 if p['id'] == proxima_pergunta_id), 
                None
            )
            
            if not pergunta_config:
                return False
            
            # ✅ Validação básica (se configurada)
            validacao = pergunta_config.get('validacao', {})
            if validacao and not self._validar_resposta(mensagem_lead, validacao):
                # Se não passar na validação, IA vai pedir de novo
                print(f"⚠️ Resposta não passou na validação: {mensagem_lead[:50]}")
                return False
            
            # ✅ Salvar resposta
            self.db.add_lead_qualificacao_resposta(
                lead_id,
                proxima_pergunta_id,
                mensagem_lead
            )
            
            print(f"📝 Resposta salva: {proxima_pergunta_id} = {mensagem_lead[:50]}")
            return True
        
        return False

    def _validar_resposta(self, resposta, validacao):
        """Valida resposta baseado nas regras configuradas"""
        # Validar mínimo de palavras
        if 'min_palavras' in validacao:
            palavras = resposta.strip().split()
            if len(palavras) < validacao['min_palavras']:
                return False
        
        # Validar regex
        if 'regex' in validacao:
            if not re.match(validacao['regex'], resposta):
                return False
        
        return True

    def get_estatisticas(self):
        """Retorna estatísticas do assistente de IA"""
        stats = {
            "ia_habilitada": self.config.get("ia_habilitada", False),
            "openai_disponivel": self.openai_habilitada,
            "total_perguntas": len(self.config.get("perguntas_qualificacao", [])),
            "modelo": self.config.get("modelo", "N/A"),
            "triagem_ativa": self.triagem is not None,
            "automacoes_ativas": self.automacoes is not None
        }
        
        # ✅ Adicionar estatísticas das automações
        if self.automacoes:
            try:
                relatorio = self.automacoes.gerar_relatorio_automacoes()
                stats['automacoes'] = relatorio
            except:
                pass
        
        return stats
    
    def obter_metricas_completas(self):
        """Retorna métricas completas incluindo triagem e automações"""
        return self.get_estatisticas()


# ✅ Função auxiliar para uso rápido
def inicializar_ia_assistant(database, whatsapp_service=None, config_path="ia_config.json"):
    """
    Inicializa IAAssistant com verificação de dependências
    
    Returns:
        IAAssistant ou None se falhar
    """
    try:
        ia = IAAssistant(database, whatsapp_service, config_path)
        print("✅ IAAssistant inicializado com sucesso")
        return ia
    except Exception as e:
        print(f"❌ Erro ao inicializar IAAssistant: {e}")
        return None