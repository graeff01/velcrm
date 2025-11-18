# -*- coding: utf-8 -*-
"""
🤖 IA ASSISTANT v4.0 CONVERSACIONAL - VERSÃO FINAL
✨ IA Empática e Natural - Pronta para Produção

CARACTERÍSTICAS:
🗣️ Conversação natural (não interrogatório)
❤️ Empatia e contexto emocional  
🎯 Perguntas abertas
🧠 Extração inteligente de informações
🎭 Adapta tom ao contexto
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
    Motor de Qualificação Conversacional v4.0
    Foco: Conversação Natural + Empatia + Inteligência
    """
    
    def __init__(self, database, whatsapp_service=None, config_path="ia_config.json"):
        """Inicializa o assistente conversacional"""
        self.db = database
        self.whatsapp = whatsapp_service
        self.config_path = config_path
        self.config = self._carregar_config(config_path)

        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_habilitada = bool(api_key)

        if self.openai_habilitada:
            self.client = OpenAI(api_key=api_key)
            print("✅ OpenAI inicializada - Modo Conversacional Ativo 🗣️")
        else:
            self.client = None
            print("⚠️ OpenAI não disponível - Modo fallback conversacional")

        # Sistema de Triagem
        try:
            self.triagem = TriagemInteligente(config_path=self.config_path)
            print("✅ Sistema de Triagem Inteligente inicializado")
        except Exception as e:
            print(f"⚠️ Triagem em modo fallback: {e}")
            self.triagem = None
        
        # Automações
        try:
            if whatsapp_service:
                self.automacoes = AutomacoesPoderosas(
                    config_path=self.config_path,
                    whatsapp_service=whatsapp_service
                )
                print("✅ Sistema de Automações inicializado")
            else:
                self.automacoes = None
        except Exception as e:
            print(f"⚠️ Automações desabilitadas: {e}")
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
        """Configuração padrão conversacional"""
        return {
            "ia_habilitada": True,
            "empresa": "MinhaEmpresa",
            "modelo": "gpt-4o-mini",
            "max_tokens": 200,
            "temperature": 0.8,
            "saudacao": "Oi! 👋 Tudo bem? Como posso te ajudar hoje? 😊",
            "perguntas_qualificacao": [
                {"id": "nome", "pergunta": "Qual seu nome?", "obrigatoria": True},
                {"id": "interesse", "pergunta": "O que você procura?", "obrigatoria": True}
            ]
        }

    # ========================================
    # 💬 PROCESSADOR CONVERSACIONAL
    # ========================================

    def processar_mensagem(self, lead_id, mensagem_lead):
        """
        ✨ Processador Conversacional v4.0
        Conversa naturalmente enquanto coleta informações
        """
        try:
            print(f"\n{'='*70}")
            print(f"💬 CONVERSANDO COM LEAD {lead_id}")
            print(f"📩 Mensagem: {mensagem_lead[:100]}...")
            print(f"{'='*70}\n")
            
            # 1. Verificações iniciais
            if not self.config.get("ia_habilitada", False):
                print("⚠️ IA desabilitada")
                return None

            lead = self.db.get_lead(lead_id)
            if not lead:
                print(f"❌ Lead {lead_id} não encontrado")
                return None

            # 2. Buscar histórico
            historico = self.db.get_messages_by_lead(lead_id)
            total_msgs = len(historico)
            print(f"📊 Total de mensagens: {total_msgs}")
            
            # 3. Detectar pedido de humano
            if self._detectar_pedido_humano(mensagem_lead):
                print("🔀 Lead pediu atendimento humano")
                self._escalar_para_humano(lead_id)
                return self.config.get("mensagem_escalar", 
                    "Claro! Vou te conectar com um especialista. Só um momento! 👨‍💼")

            # 4. Verificar se já qualificado
            if lead.get('ai_qualified', False):
                print(f"⏭️ Lead já qualificado")
                return None

            # 5. 🎬 PRIMEIRA MENSAGEM
            if total_msgs == 1:
                print("🎬 PRIMEIRA CONVERSA - Gerando saudação empática")
                resposta = self._gerar_saudacao_empatica(mensagem_lead)
                self.db.add_message(lead_id, 'ia', 'Assistente IA', resposta)
                print(f"✅ Saudação: {resposta[:80]}...")
                return resposta

            # 6. Timeout
            if self._timeout_expirado(lead_id):
                print("⏰ Timeout - Escalando")
                self._escalar_para_humano(lead_id)
                return "Opa! Vou te conectar com a equipe para continuar. 👋"

            # 7. 🧠 EXTRAIR INFORMAÇÕES SILENCIOSAMENTE
            print("🧠 Extraindo informações da conversa...")
            self._extrair_informacoes_naturalmente(lead_id, mensagem_lead, historico)
            
            # 8. Verificar se pode finalizar
            if self._pronto_para_finalizar(lead_id, historico):
                print("🎯 Informações suficientes - Finalizando")
                return self._finalizar_naturalmente(lead_id, historico)

            # 9. 💬 GERAR RESPOSTA CONVERSACIONAL
            print("💬 Gerando resposta natural...")
            
            if self.openai_habilitada and self.client:
                resposta = self._gerar_resposta_openai(lead_id, mensagem_lead, historico)
            else:
                resposta = self._gerar_resposta_fallback(lead_id, mensagem_lead)
            
            if resposta:
                self.db.add_message(lead_id, 'ia', 'Assistente IA', resposta)
                self.db.add_lead_log(lead_id, 'ia_respondeu', 'IA Assistant', 
                    f'Resposta: {resposta[:50]}...')
                print(f"✅ Enviado: {resposta[:80]}...\n")
            
            return resposta

        except Exception as e:
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return "Ops! Tive um probleminha. Vou chamar alguém da equipe! 😊"

    # ========================================
    # 🎭 SAUDAÇÕES E RESPOSTAS NATURAIS
    # ========================================

    def _gerar_saudacao_empatica(self, primeira_mensagem):
        """Gera saudação que responde ao contexto da primeira mensagem"""
        msg_lower = primeira_mensagem.lower()
        empresa = self.config.get("empresa", "nossa empresa")
        
        # Detectar URGÊNCIA
        if any(kw in msg_lower for kw in ['urgente', 'rápido', 'agora', 'já', 'hoje', 'imediato']):
            return f"Oi! 👋 Vi que você está com urgência! Relaxa, vou te ajudar rapidinho. Me conta mais sobre o que você precisa?"
        
        # Detectar PROBLEMA
        if any(kw in msg_lower for kw in ['problema', 'ajuda', 'dificuldade', 'perdendo', 'dor de cabeça', 'complicado']):
            return f"Oi! 👋 Entendo que você está enfrentando uma dificuldade. Fica tranquilo, vamos resolver isso juntos! Me conta o que está acontecendo?"
        
        # Detectar INTERESSE ESPECÍFICO
        if any(kw in msg_lower for kw in ['crm', 'sistema', 'software', 'ferramenta', 'plataforma', 'solução']):
            return f"Oi! 👋 Que legal que você se interessou por nossas soluções! Me conta um pouco sobre o que você está buscando?"
        
        # Detectar ORÇAMENTO/PREÇO
        if any(kw in msg_lower for kw in ['quanto custa', 'preço', 'valor', 'orçamento', 'investimento']):
            return f"Oi! 👋 Legal que você quer saber sobre valores! Antes de falar de investimento, me conta: o que você está procurando? Assim consigo te passar o melhor preço!"
        
        # Saudação GENÉRICA mas amigável
        return f"Oi! 👋 Tudo bem? Sou a assistente virtual da {empresa}! Como posso te ajudar hoje? 😊"

    def _gerar_resposta_openai(self, lead_id, mensagem_lead, historico):
        """Gera resposta natural usando OpenAI"""
        try:
            # Buscar informações já coletadas
            respostas = self.db.get_lead_qualificacao_respostas(lead_id)
            info_coletada = {r['pergunta_id']: r['resposta'] for r in respostas}
            
            # Construir contexto
            contexto = self._construir_contexto_ia(lead_id, historico, mensagem_lead, info_coletada)
            
            # Chamar OpenAI
            response = self.client.chat.completions.create(
                model=self.config.get("modelo", "gpt-4o-mini"),
                messages=contexto,
                max_tokens=self.config.get("max_tokens", 200),
                temperature=self.config.get("temperature", 0.8)
            )
            
            resposta = response.choices[0].message.content.strip()
            print(f"🤖 OpenAI gerou resposta natural")
            return resposta
            
        except Exception as e:
            print(f"❌ Erro OpenAI: {e}")
            return self._gerar_resposta_fallback(lead_id, mensagem_lead)

    def _construir_contexto_ia(self, lead_id, historico, mensagem_atual, info_coletada):
        """Constrói contexto conversacional para OpenAI"""
        empresa = self.config.get("empresa", "Nossa Empresa")
        
        # PROMPT DO SISTEMA - Define personalidade
        prompt_base = self.config.get("prompt_sistema", "")
        
        prompt_sistema = f"""Você é a assistente virtual conversacional da {empresa}.

🎭 SUA PERSONALIDADE:
- Natural e empática (como um amigo prestativo, NÃO um robô)
- Positiva e animada (use 1-2 emojis por mensagem)
- Responda em 2-4 frases curtas no máximo

💬 COMO CONVERSAR (MUITO IMPORTANTE):
- NÃO faça perguntas diretas tipo "Qual seu orçamento?"
- FAÇA perguntas abertas tipo "Me conta mais sobre isso..."
- Demonstre empatia: "Imagino que isso deve ser frustrante..."
- Continue a conversa naturalmente
- Se o lead menciona urgência → mostre que entende
- Se o lead menciona problema → demonstre vontade de ajudar
- Se o lead dá informações → agradeça antes da próxima pergunta

🎯 INFORMAÇÕES QUE PRECISA COLETAR (de forma NATURAL):
- Nome do lead
- O que ele precisa/busca  
- Orçamento (se mencionar)
- Prazo/urgência (se mencionar)
- Tamanho da equipe/empresa (se relevante)

"""
        
        # Adicionar o que já sabemos
        if info_coletada:
            prompt_sistema += "\n📋 O QUE JÁ SABEMOS:\n"
            for tipo, valor in info_coletada.items():
                prompt_sistema += f"- {tipo}: {valor[:50]}...\n"
        else:
            prompt_sistema += "\n📋 O QUE JÁ SABEMOS: Nada ainda, estamos começando!\n"
        
        # Sugerir o que perguntar a seguir
        faltam = self._o_que_falta_descobrir(info_coletada)
        if faltam:
            prompt_sistema += f"\n💡 SUGESTÃO: Tente descobrir sobre {faltam[0]}, mas de forma NATURAL!\n"
            prompt_sistema += "Não pergunte diretamente! Deixe fluir na conversa.\n"
        
        # Adicionar instruções do config se existir
        if prompt_base:
            prompt_sistema += f"\n{prompt_base}\n"
        
        # Histórico da conversa
        mensagens = [{"role": "system", "content": prompt_sistema}]
        
        for msg in historico[-10:]:  # Últimas 10 mensagens
            role = "user" if msg['sender_type'] == 'lead' else "assistant"
            mensagens.append({"role": role, "content": msg['content']})
        
        return mensagens

    def _o_que_falta_descobrir(self, info_coletada):
        """Retorna lista do que ainda não descobrimos"""
        essenciais = ['nome', 'interesse', 'orcamento', 'prazo']
        opcionais = ['contato', 'empresa', 'tamanho_empresa']
        
        # Priorizar essenciais
        faltam_essenciais = [item for item in essenciais if item not in info_coletada]
        if faltam_essenciais:
            return faltam_essenciais
        
        # Depois opcionais
        faltam_opcionais = [item for item in opcionais if item not in info_coletada]
        return faltam_opcionais

    def _gerar_resposta_fallback(self, lead_id, mensagem_lead):
        """Gera resposta natural SEM OpenAI"""
        msg_lower = mensagem_lead.lower()
        
        # Detectar URGÊNCIA
        if any(kw in msg_lower for kw in ['urgente', 'rápido', 'agora', 'hoje', 'já']):
            return "Entendi a urgência! 🚀 Me conta mais detalhes para eu conseguir te ajudar rápido?"
        
        # Detectar ORÇAMENTO mencionado
        if any(kw in msg_lower for kw in ['real', 'mil', 'r$', 'reais', 'valor']):
            return "Legal! E me conta, qual o prazo que você está pensando para isso?"
        
        # Detectar INTERESSE em produto
        if any(kw in msg_lower for kw in ['crm', 'sistema', 'software', 'ferramenta']):
            return "Show! E me diz, é para você ou tem uma equipe que vai usar?"
        
        # Detectar TAMANHO mencionado
        if any(kw in msg_lower for kw in ['pessoas', 'funcionários', 'vendedores', 'equipe']):
            return "Entendi! E me conta, vocês já usam algum sistema hoje ou estão começando do zero?"
        
        # Resposta GENÉRICA natural
        return "Entendi! Me conta mais sobre isso? Quanto mais detalhes, melhor consigo te ajudar! 😊"

    # ========================================
    # 🧠 EXTRAÇÃO INTELIGENTE DE INFORMAÇÕES
    # ========================================

    def _extrair_informacoes_naturalmente(self, lead_id, mensagem, historico):
        """
        Extrai informações SEM interromper a conversa
        Lead não percebe que estamos salvando
        """
        try:
            respostas_existentes = self.db.get_lead_qualificacao_respostas(lead_id)
            ids_respondidas = [r['pergunta_id'] for r in respostas_existentes]
            
            msg_lower = mensagem.lower()
            
            # 🔍 NOME
            if 'nome' not in ids_respondidas:
                nome = self._extrair_nome(mensagem, msg_lower, historico)
                if nome:
                    self._salvar_silenciosamente(lead_id, 'nome', nome, 'name', 20)
            
            # 🔍 INTERESSE
            if 'interesse' not in ids_respondidas:
                interesse = self._extrair_interesse(mensagem, msg_lower)
                if interesse:
                    score = 25 if len(interesse) > 30 else 15
                    self._salvar_silenciosamente(lead_id, 'interesse', interesse, 'interesse', score)
            
            # 🔍 ORÇAMENTO
            if 'orcamento' not in ids_respondidas:
                orcamento = self._extrair_orcamento(mensagem, msg_lower)
                if orcamento:
                    score = self._calcular_score_orcamento(orcamento)
                    self._salvar_silenciosamente(lead_id, 'orcamento', orcamento, 'orcamento', score)
            
            # 🔍 PRAZO
            if 'prazo' not in ids_respondidas:
                prazo = self._extrair_prazo(mensagem, msg_lower)
                if prazo:
                    score = self._calcular_score_prazo(msg_lower)
                    self._salvar_silenciosamente(lead_id, 'prazo', prazo, 'prazo', score)
            
            # 🔍 CONTATO
            if 'contato' not in ids_respondidas:
                contato = self._extrair_preferencia_contato(mensagem, msg_lower)
                if contato:
                    self._salvar_silenciosamente(lead_id, 'contato', contato, 'preferencia_contato', 15)
            
            # 🔍 TIPO CLIENTE
            if 'empresa' not in ids_respondidas:
                tipo = self._extrair_tipo_cliente(mensagem, msg_lower)
                if tipo:
                    score = 20 if 'empresa' in tipo.lower() else 10
                    self._salvar_silenciosamente(lead_id, 'empresa', tipo, 'tipo_cliente', score)
            
            # 🔍 TAMANHO
            if 'tamanho_empresa' not in ids_respondidas:
                tamanho = self._extrair_tamanho(mensagem, msg_lower)
                if tamanho:
                    score = self._calcular_score_tamanho(tamanho)
                    self._salvar_silenciosamente(lead_id, 'tamanho_empresa', tamanho, 'tamanho_empresa', score)
            
        except Exception as e:
            print(f"⚠️ Erro na extração: {e}")

    def _salvar_silenciosamente(self, lead_id, tipo, valor, campo_lead, score):
        """Salva informação sem fazer alarde"""
        try:
            # Salvar na tabela de respostas
            self.db.add_lead_qualificacao_resposta(lead_id, tipo, valor)
            
            # Atualizar campo do lead
            self._atualizar_campo_lead(lead_id, campo_lead, valor)
            
            # Incrementar score
            self._incrementar_score(lead_id, score)
            
            print(f"💾 [Silencioso] {tipo}: '{valor[:30]}...' (+{score} pts)")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar {tipo}: {e}")
            return False

    # ========================================
    # 🔍 EXTRATORES ESPECIALIZADOS
    # ========================================

    def _extrair_nome(self, mensagem, msg_lower, historico):
        """Extrai nome completo de forma inteligente"""
        # Padrão 1: "Meu nome é..."
        match = re.search(r'(?:meu nome é|me chamo|sou o|sou a|sou)\s+([A-Za-zÀ-ÿ\s]{3,50})', mensagem, re.I)
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'\s+(e|,|\.)\s+.*$', '', nome)  # Remove sufixos
            if len(nome.split()) >= 2:
                return nome
        
        # Padrão 2: Duas palavras só com letras no início
        palavras = mensagem.strip().split()
        if len(palavras) >= 2:
            if all(re.match(r'^[A-Za-zÀ-ÿ]+$', p) for p in palavras[:2]):
                # Excluir keywords comuns
                excluir = ['quero', 'preciso', 'tenho', 'ola', 'oi', 'bom', 'dia', 'tarde', 'noite']
                primeiro_nome = palavras[0].lower()
                
                if primeiro_nome not in excluir:
                    return f"{palavras[0]} {palavras[1]}"
        
        return None

    def _extrair_interesse(self, mensagem, msg_lower):
        """Extrai interesse/necessidade"""
        keywords = [
            'crm', 'sistema', 'software', 'ferramenta', 'plataforma',
            'quero', 'preciso', 'busco', 'procuro', 'gostaria',
            'solução', 'produto', 'serviço', 'gestão', 'controle',
            'automação', 'integração', 'vendas', 'atendimento'
        ]
        
        if any(kw in msg_lower for kw in keywords):
            return mensagem.strip()
        
        return None

    def _extrair_orcamento(self, mensagem, msg_lower):
        """Extrai orçamento/investimento"""
        patterns = [
            r'R\$\s*\d+',
            r'\d+\s*(mil|k|reais)',
            r'\d{3,}'
        ]
        
        if any(re.search(p, mensagem, re.I) for p in patterns):
            return mensagem.strip()
        
        if any(kw in msg_lower for kw in ['grátis', 'gratuito', 'barato', 'investimento', 'orçamento']):
            return mensagem.strip()
        
        return None

    def _extrair_prazo(self, mensagem, msg_lower):
        """Extrai prazo/urgência"""
        keywords = [
            'urgente', 'hoje', 'agora', 'já', 'imediato',
            'semana', 'dia', 'mês', 'prazo', 'rápido', 'breve'
        ]
        
        if any(kw in msg_lower for kw in keywords):
            return mensagem.strip()
        
        return None

    def _extrair_preferencia_contato(self, mensagem, msg_lower):
        """Extrai preferência de contato"""
        if 'whatsapp' in msg_lower or 'zap' in msg_lower:
            return "WhatsApp"
        elif 'email' in msg_lower or 'e-mail' in msg_lower:
            return "Email"
        elif 'telefone' in msg_lower or 'ligar' in msg_lower:
            return "Telefone"
        elif 'qualquer' in msg_lower:
            return "Qualquer um"
        
        return None

    def _extrair_tipo_cliente(self, mensagem, msg_lower):
        """Extrai tipo de cliente"""
        if any(kw in msg_lower for kw in ['empresa', 'negócio', 'corporativo', 'cnpj']):
            return "Empresa"
        elif any(kw in msg_lower for kw in ['pessoal', 'particular', 'uso próprio']):
            return "Pessoal"
        
        return None

    def _extrair_tamanho(self, mensagem, msg_lower):
        """Extrai tamanho da empresa/equipe"""
        patterns = [
            r'\d+\s*(?:funcionário|pessoas|colaborador|vendedor)',
            r'(?:equipe|time)\s+de\s+\d+'
        ]
        
        if any(re.search(p, mensagem, re.I) for p in patterns):
            return mensagem.strip()
        
        if any(kw in msg_lower for kw in ['pequena', 'média', 'grande', 'startup', 'mei']):
            return mensagem.strip()
        
        return None

    # ========================================
    # 💰 CALCULADORES DE SCORE
    # ========================================

    def _calcular_score_orcamento(self, mensagem):
        """Calcula score baseado no orçamento"""
        valores = re.findall(r'\d+', mensagem)
        if valores:
            valor = int(valores[0])
            if 'mil' in mensagem.lower() or 'k' in mensagem.lower():
                valor *= 1000
            
            # Usar ranges do config se disponível
            ranges = self.config.get("perguntas_qualificacao", [])
            orcamento_config = next((p for p in ranges if p.get('id') == 'orcamento'), None)
            
            if orcamento_config and 'ranges' in orcamento_config:
                if valor >= orcamento_config['ranges'].get('premium', {}).get('min', 10000):
                    return orcamento_config['score'].get('premium', 30)
                elif valor >= orcamento_config['ranges'].get('alto', {}).get('min', 5000):
                    return orcamento_config['score'].get('alto', 25)
                elif valor >= orcamento_config['ranges'].get('medio', {}).get('min', 2000):
                    return orcamento_config['score'].get('medio', 15)
            else:
                # Fallback
                if valor >= 50000:
                    return 30
                elif valor >= 10000:
                    return 25
                elif valor >= 5000:
                    return 20
                else:
                    return 10
        
        return 10

    def _calcular_score_prazo(self, msg_lower):
        """Calcula score baseado na urgência"""
        # Usar keywords do config se disponível
        prazo_config = next((p for p in self.config.get("perguntas_qualificacao", []) 
                            if p.get('id') == 'prazo'), None)
        
        if prazo_config and 'keywords_urgencia' in prazo_config:
            keywords = prazo_config['keywords_urgencia']
            if any(kw in msg_lower for kw in keywords.get('imediato', [])):
                return prazo_config['score'].get('urgente', 25)
            elif any(kw in msg_lower for kw in keywords.get('curto', [])):
                return prazo_config['score'].get('curto', 20)
            elif any(kw in msg_lower for kw in keywords.get('medio', [])):
                return prazo_config['score'].get('medio', 10)
        else:
            # Fallback
            if any(kw in msg_lower for kw in ['hoje', 'agora', 'urgente', 'já', 'imediato']):
                return 25
            elif any(kw in msg_lower for kw in ['semana', 'breve', 'rápido']):
                return 15
        
        return 5

    def _calcular_score_tamanho(self, mensagem):
        """Calcula score baseado no tamanho"""
        valores = re.findall(r'\d+', mensagem)
        if valores:
            num = int(valores[0])
            
            # Usar ranges do config se disponível
            tamanho_config = next((p for p in self.config.get("perguntas_qualificacao", []) 
                                  if p.get('id') == 'tamanho_empresa'), None)
            
            if tamanho_config and 'ranges' in tamanho_config:
                if num >= tamanho_config['ranges'].get('grande', {}).get('min', 50):
                    return tamanho_config['score'].get('grande', 30)
                elif num >= tamanho_config['ranges'].get('media', {}).get('min', 10):
                    return tamanho_config['score'].get('media', 20)
            else:
                # Fallback
                if num >= 200:
                    return 30
                elif num >= 50:
                    return 25
                elif num >= 10:
                    return 20
        
        return 10

    # ========================================
    # 🎯 FINALIZAÇÃO
    # ========================================

    def _pronto_para_finalizar(self, lead_id, historico):
        """Verifica se pode finalizar a qualificação"""
        respostas = self.db.get_lead_qualificacao_respostas(lead_id)
        ids = [r['pergunta_id'] for r in respostas]
        
        # Critério 1: Tem informações mínimas
        tem_nome = 'nome' in ids
        tem_interesse = 'interesse' in ids
        tem_info_comercial = 'orcamento' in ids or 'prazo' in ids
        
        info_minima = tem_nome and tem_interesse and tem_info_comercial
        
        # Critério 2: Trocou mensagens suficientes (10+)
        msgs_suficientes = len(historico) >= 10
        
        # Critério 3: Coletou 5+ informações
        info_completa = len(respostas) >= 5
        
        return info_minima and (msgs_suficientes or info_completa)

    def _finalizar_naturalmente(self, lead_id, historico):
        """Finaliza conversa de forma natural"""
        try:
            print("\n🎯 FINALIZANDO CONVERSA...")
            
            lead = self.db.get_lead(lead_id)
            respostas_db = self.db.get_lead_qualificacao_respostas(lead_id)
            
            # Construir dict de respostas
            respostas_dict = {r['pergunta_id']: r['resposta'] for r in respostas_db}
            
            # Calcular score
            if self.triagem:
                score_data = self.triagem.calcular_score_completo(respostas_dict, historico)
                print(f"🎯 SCORE: {score_data['score_total']}/175 - {score_data['classificacao'].upper()}")
            else:
                score_data = {
                    'score_total': 65,
                    'classificacao': 'warm',
                    'prioridade': 'normal',
                    'is_vip': False,
                    'sentimento': 'positivo',
                    'qualificado': True
                }
            
            # Atualizar banco
            self._atualizar_lead_qualificado(lead_id, respostas_dict, score_data)
            
            # Mensagem final PERSONALIZADA
            nome = respostas_dict.get('nome', lead.get('name', 'amigo'))
            
            # Usar mensagens do config se disponível
            msgs_config = self.config.get('mensagens_personalizadas', {})
            
            if score_data['score_total'] >= 80:
                msg_base = msgs_config.get('score_alto', 
                    "Vejo que você tem um projeto incrível! 🌟")
                msg_final = f"Perfeito, {nome}! ✅\n\n{msg_base}\n\nVou te conectar com um de nossos especialistas top agora. Ele já sabe tudo que conversamos! 😊"
            
            elif score_data['score_total'] >= 50:
                msg_base = msgs_config.get('score_medio',
                    "Temos ótimas soluções para você! 💼")
                msg_final = f"Ótimo, {nome}! ✅\n\n{msg_base}\n\nVou te passar para um especialista que vai te mostrar tudo. Ele já está por dentro da nossa conversa! 👍"
            
            else:
                msg_base = msgs_config.get('score_baixo',
                    "Vamos encontrar algo que funcione para você!")
                msg_final = f"Legal, {nome}! 😊\n\n{msg_base}\n\nVou conectar você com a equipe. Um momento..."
            
            self.db.add_message(lead_id, 'ia', 'Assistente IA', msg_final)
            
            # Automações
            if self.automacoes:
                lead_data = {'id': lead_id, 'name': lead.get('name'), 
                           'phone': lead.get('phone'), **respostas_dict}
                processar_lead_qualificado(lead_data, score_data, 
                                         self.whatsapp, self.config_path)
            
            print("✅ Finalizado naturalmente!\n")
            return msg_final
        
        except Exception as e:
            print(f"❌ Erro ao finalizar: {e}")
            return "Perfeito! Vou te conectar com a equipe agora! 😊"

    def _atualizar_lead_qualificado(self, lead_id, respostas_dict, score_data):
        """Atualiza lead no banco"""
        try:
            campos_update = {
                'ai_qualified': 1,
                'qualification_score': score_data['score_total'],
                'classification': score_data['classificacao'],
                'prioridade': score_data['prioridade'],
                'sentimento': score_data['sentimento'],
                'status': 'qualificado'
            }
            
            # Adicionar campos de respostas
            if 'nome' in respostas_dict:
                campos_update['name'] = respostas_dict['nome']
            
            for campo in ['interesse', 'orcamento', 'prazo', 'preferencia_contato', 
                         'tipo_cliente', 'tamanho_empresa']:
                if campo in respostas_dict:
                    campos_update[campo] = respostas_dict[campo]
            
            # Executar UPDATE
            set_clause = ', '.join([f"{k} = ?" for k in campos_update.keys()])
            values = list(campos_update.values()) + [lead_id]
            
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            
            # Log
            self.db.add_lead_log(lead_id, 'ia_qualificado_completo', 'IA Conversacional',
                f'Score: {score_data["score_total"]}/175 - {score_data["classificacao"].upper()}')
            
            print("✅ Lead atualizado no banco")
        except Exception as e:
            print(f"❌ Erro ao atualizar lead: {e}")

    # ========================================
    # 🛠️ MÉTODOS AUXILIARES
    # ========================================

    def _incrementar_score(self, lead_id, pontos):
        """Incrementa score do lead"""
        try:
            lead = self.db.get_lead(lead_id)
            score_atual = lead.get('qualification_score', 0)
            novo_score = min(175, score_atual + pontos)
            
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute("UPDATE leads SET qualification_score = ? WHERE id = ?", 
                     (novo_score, lead_id))
            conn.commit()
            conn.close()
            
            print(f"📊 Score: {score_atual} → {novo_score}")
        except Exception as e:
            print(f"❌ Erro ao incrementar score: {e}")

    def _atualizar_campo_lead(self, lead_id, campo, valor):
        """Atualiza campo específico do lead"""
        campos_validos = [
            'name', 'interesse', 'orcamento', 'prazo', 'preferencia_contato',
            'tipo_cliente', 'tamanho_empresa'
        ]
        
        if campo not in campos_validos:
            return
        
        try:
            conn = self.db.get_connection()
            c = conn.cursor()
            c.execute(f"UPDATE leads SET {campo} = ? WHERE id = ?", (valor, lead_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao atualizar campo {campo}: {e}")

    def _detectar_pedido_humano(self, mensagem):
        """Detecta se lead quer falar com humano"""
        keywords = self.config.get("keywords_humano", [
            "atendente", "humano", "pessoa", "alguém", "falar com"
        ])
        
        msg_lower = mensagem.lower()
        return any(kw.lower() in msg_lower for kw in keywords)

    def _escalar_para_humano(self, lead_id):
        """Escala lead para atendimento humano"""
        self.db.update_lead_status(lead_id, "novo")
        self.db.add_lead_log(lead_id, "ia_escalado_humano", "IA Assistant", 
                           "Lead solicitou atendimento humano")
        print(f"🔀 Lead {lead_id} escalado para humano")

    def _timeout_expirado(self, lead_id):
        """Verifica se timeout de qualificação expirou"""
        timeout_min = self.config.get("timeout_qualificacao_minutos", 30)
        lead = self.db.get_lead(lead_id)
        
        if not lead or not lead.get('created_at'):
            return False
        
        try:
            created_at = datetime.fromisoformat(lead['created_at'])
            return datetime.now() - created_at > timedelta(minutes=timeout_min)
        except:
            return False

    # ========================================
    # 📊 ESTATÍSTICAS
    # ========================================

    def get_estatisticas(self):
        """Retorna estatísticas do sistema"""
        return {
            "versao": "4.0 Conversacional",
            "modo": "Empático e Natural",
            "ia_habilitada": self.config.get("ia_habilitada", False),
            "openai_disponivel": self.openai_habilitada,
            "modelo": self.config.get("modelo", "N/A"),
            "total_perguntas": len(self.config.get("perguntas_qualificacao", [])),
            "triagem_ativa": self.triagem is not None,
            "automacoes_ativas": self.automacoes is not None
        }
    
    def obter_metricas_completas(self):
        """Métricas completas do sistema"""
        return self.get_estatisticas()


# ========================================
# 🚀 INICIALIZADOR
# ========================================

def inicializar_ia_assistant(database, whatsapp_service=None, config_path="ia_config.json"):
    """
    Inicializa IA Conversacional v4.0
    
    Args:
        database: Instância do Database
        whatsapp_service: Instância do WhatsAppService (opcional)
        config_path: Caminho para ia_config.json
    
    Returns:
        IAAssistant: Instância da IA ou None se erro
    """
    try:
        ia = IAAssistant(database, whatsapp_service, config_path)
        print("✅ IA Conversacional v4.0 inicializada com sucesso! 🗣️")
        return ia
    except Exception as e:
        print(f"❌ Erro ao inicializar IA: {e}")
        import traceback
        traceback.print_exc()
        return None