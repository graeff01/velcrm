"""
🤖 IA ASSISTANT - Motor de Qualificação de Leads
Responsável por:
- Conversar com leads automaticamente
- Fazer perguntas de qualificação
- Detectar quando escalar para humano
- Marcar leads como qualificados
"""

import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
import re


class IAAssistant:
    def __init__(self, database, config_path="ia_config.json"):
        """
        Inicializa o assistente de IA

        Args:
            database: Instância do Database
            config_path: Caminho para arquivo de configuração
        """
        self.db = database
        self.config = self._carregar_config(config_path)

        # Inicializar OpenAI (se API key disponível)
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_habilitada = bool(api_key)

        if self.openai_habilitada:
            self.client = OpenAI(api_key=api_key)
            print("✅ OpenAI inicializada")
        else:
            print("⚠️ OPENAI_API_KEY não encontrada - usando fallback")

    def _carregar_config(self, path):
        """Carrega configuração do JSON"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), path)
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
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
        Processa mensagem do lead e retorna resposta da IA

        Returns:
            str: Resposta da IA (ou None se não deve responder)
        """
        try:
            # Verificar se IA está habilitada
            if not self.config.get("ia_habilitada", False):
                return None

            lead = self.db.get_lead(lead_id)
            if not lead:
                return None

            # 1. Verificar se lead quer falar com humano
            if self._detectar_pedido_humano(mensagem_lead):
                self._escalar_para_humano(lead_id)
                return self.config.get("mensagem_escalar",
                    "Vou conectar você com um atendente agora!")

            # 2. Verificar se já está qualificado ou atribuído
            if lead['status'] in ['qualificado', 'em_atendimento', 'ganho', 'perdido']:
                return None  # Não responder, já passou pela IA

            # 3. Verificar se é primeira mensagem (enviar saudação)
            historico = self.db.get_messages_by_lead(lead_id)
            if len(historico) == 1:  # Apenas a mensagem do lead
                return self._gerar_saudacao()

            # 4. Verificar timeout de qualificação
            if self._timeout_expirado(lead_id):
                self._escalar_para_humano(lead_id)
                return "Vou te conectar com um atendente para continuar. 👨‍💼"

            # 5. Verificar quantas perguntas já foram respondidas
            perguntas_respondidas = self.db.get_lead_qualificacao_respostas(lead_id)
            total_perguntas = len(self.config["perguntas_qualificacao"])

            # 6. Se respondeu todas as obrigatórias, qualificar
            if self._todas_obrigatorias_respondidas(lead_id):
                resumo = self._gerar_resumo_qualificacao(lead_id)
                self._marcar_lead_qualificado(lead_id)

                nome = lead.get('name', 'Cliente')
                mensagem = self.config.get("mensagem_qualificado", "Obrigado!")
                return mensagem.format(nome=nome, resumo=resumo)

            # 7. Gerar próxima pergunta com IA
            if self.openai_habilitada:
                return self._gerar_resposta_ia(lead_id, mensagem_lead, historico)
            else:
                # Fallback: fazer perguntas sequencialmente sem IA
                return self._proxima_pergunta_sequencial(lead_id)

        except Exception as e:
            print(f"❌ Erro ao processar mensagem IA: {e}")
            import traceback
            traceback.print_exc()
            return None

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

    def _gerar_resumo_qualificacao(self, lead_id):
        """Gera resumo das informações coletadas"""
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        perguntas_config = {p['id']: p for p in self.config.get("perguntas_qualificacao", [])}

        resumo_linhas = []
        for resp in respostas:
            pergunta_id = resp['pergunta_id']
            if pergunta_id in perguntas_config:
                pergunta_texto = perguntas_config[pergunta_id]['pergunta']
                # Simplificar pergunta para resumo
                label = pergunta_texto.split('?')[0].replace('Qual seu ', '').replace('Qual ', '')
                resumo_linhas.append(f"• {label}: {resp['resposta']}")

        return "\n".join(resumo_linhas) if resumo_linhas else "Informações coletadas"

    def _marcar_lead_qualificado(self, lead_id):
        """Marca lead como qualificado pela IA"""
        self.db.update_lead_status(lead_id, "qualificado")
        self.db.add_lead_log(
            lead_id,
            "ia_qualificado",
            "IA Assistant",
            "Lead qualificado automaticamente pela IA"
        )
        print(f"✅ Lead {lead_id} qualificado pela IA")

    def _proxima_pergunta_sequencial(self, lead_id):
        """Faz próxima pergunta sem usar IA (modo sequencial)"""
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        ids_respondidas = [r['pergunta_id'] for r in respostas]

        perguntas = self.config.get("perguntas_qualificacao", [])

        for pergunta in perguntas:
            if pergunta['id'] not in ids_respondidas:
                # Salvar que está aguardando resposta desta pergunta
                self.db.set_lead_proxima_pergunta(lead_id, pergunta['id'])
                return pergunta['pergunta']

        return "Obrigado pelas informações! 😊"

    def _gerar_resposta_ia(self, lead_id, mensagem_lead, historico):
        """Gera resposta usando OpenAI"""
        try:
            # Construir contexto da conversa
            contexto = self._construir_contexto_ia(lead_id, historico)

            # Chamar OpenAI
            response = self.client.chat.completions.create(
                model=self.config.get("modelo", "gpt-4o-mini"),
                messages=contexto,
                max_tokens=self.config.get("max_tokens", 150),
                temperature=self.config.get("temperature", 0.7)
            )

            resposta_ia = response.choices[0].message.content.strip()

            # Analisar se a resposta da IA coletou informação relevante
            self._extrair_e_salvar_informacao(lead_id, mensagem_lead)

            return resposta_ia

        except Exception as e:
            print(f"❌ Erro ao chamar OpenAI: {e}")
            # Fallback para modo sequencial
            return self._proxima_pergunta_sequencial(lead_id)

    def _construir_contexto_ia(self, lead_id, historico):
        """Constrói contexto para a IA com histórico de mensagens"""
        mensagens = []

        # 1. Prompt do sistema
        prompt_sistema = self.config.get("prompt_sistema", "Você é um assistente virtual.")

        # Adicionar informações sobre perguntas restantes
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

        # 2. Histórico de mensagens (últimas 10)
        for msg in historico[-10:]:
            role = "user" if msg['sender_type'] == 'lead' else "assistant"
            mensagens.append({
                "role": role,
                "content": msg['content']
            })

        return mensagens

    def _extrair_e_salvar_informacao(self, lead_id, mensagem_lead):
        """Extrai informação da mensagem e associa à pergunta pendente"""
        # Verificar qual pergunta está aguardando resposta
        proxima_pergunta_id = self.db.get_lead_proxima_pergunta(lead_id)

        if proxima_pergunta_id:
            # Salvar resposta
            self.db.add_lead_qualificacao_resposta(
                lead_id,
                proxima_pergunta_id,
                mensagem_lead
            )
            print(f"📝 Resposta salva: {proxima_pergunta_id} = {mensagem_lead[:50]}")
        else:
            # Tentar detectar automaticamente qual pergunta foi respondida
            self._detectar_e_salvar_resposta_automatica(lead_id, mensagem_lead)

    def _detectar_e_salvar_resposta_automatica(self, lead_id, mensagem):
        """Tenta detectar automaticamente qual pergunta foi respondida"""
        # Heurística simples: se mensagem contém nome próprio, pode ser resposta ao nome
        # Se contém "R$" ou valores, pode ser orçamento, etc.

        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        ids_respondidas = [r['pergunta_id'] for r in respostas]

        # Nome: começa com maiúscula e tem sobrenome
        if 'nome' not in ids_respondidas and re.match(r'^[A-Z][a-z]+ [A-Z]', mensagem):
            self.db.add_lead_qualificacao_resposta(lead_id, 'nome', mensagem)
            return

        # Orçamento: contém valores monetários
        if 'orcamento' not in ids_respondidas and re.search(r'R\$|real|reais|\d+\s*mil', mensagem, re.I):
            self.db.add_lead_qualificacao_resposta(lead_id, 'orcamento', mensagem)
            return

        # Prazo: contém referências temporais
        if 'prazo' not in ids_respondidas and re.search(r'dia|semana|mês|mes|ano|urgente|breve', mensagem, re.I):
            self.db.add_lead_qualificacao_resposta(lead_id, 'prazo', mensagem)
            return

    def get_estatisticas(self):
        """Retorna estatísticas do assistente de IA"""
        return {
            "ia_habilitada": self.config.get("ia_habilitada", False),
            "openai_disponivel": self.openai_habilitada,
            "total_perguntas": len(self.config.get("perguntas_qualificacao", [])),
            "modelo": self.config.get("modelo", "N/A")
        }
