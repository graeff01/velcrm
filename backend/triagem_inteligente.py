# -*- coding: utf-8 -*-
"""
Sistema de Triagem Inteligente de Leads
Versão: 2.0.0
Compatível com ia_config.json v2.0.0
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class TriagemInteligente:
    """
    Sistema avançado de scoring e classificação de leads
    baseado nas respostas coletadas pela IA
    """
    
    def __init__(self, config_path: str = 'ia_config.json'):
        """Inicializa o sistema de triagem com configurações"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.scoring_config = self.config.get('scoring', {})
        self.perguntas = self.config.get('perguntas_qualificacao', [])
        self.analise_sentimento = self.config.get('analise_sentimento', {})
        
    
    def calcular_score_completo(self, respostas: Dict, historico_mensagens: List[Dict]) -> Dict:
        """
        Calcula o score total do lead baseado em todas as respostas
        
        Args:
            respostas: Dicionário com as respostas coletadas
            historico_mensagens: Lista de mensagens da conversa
            
        Returns:
            Dict com score, classificação, breakdown e recomendações
        """
        score_total = 0
        breakdown = {}
        
        # 1. Score das perguntas obrigatórias e opcionais
        score_perguntas, breakdown_perguntas = self._score_perguntas(respostas)
        score_total += score_perguntas
        breakdown['perguntas'] = breakdown_perguntas
        
        # 2. Score de sentimento (análise das mensagens)
        score_sentimento, sentimento = self._analisar_sentimento(historico_mensagens)
        score_total += score_sentimento
        breakdown['sentimento'] = {
            'score': score_sentimento,
            'classificacao': sentimento
        }
        
        # 3. Aplicar penalidades
        penalidades, motivos = self._aplicar_penalidades(respostas, historico_mensagens)
        score_total += penalidades
        breakdown['penalidades'] = {
            'score': penalidades,
            'motivos': motivos
        }
        
        # 4. Classificar lead
        classificacao, prioridade = self._classificar_lead(score_total, respostas)
        
        # 5. Verificar se é VIP
        is_vip = self._detectar_vip(respostas, score_total)
        
        # 6. Gerar recomendações
        recomendacoes = self._gerar_recomendacoes(
            score_total, classificacao, respostas, sentimento
        )
        
        return {
            'score_total': max(0, score_total),  # Nunca negativo
            'score_maximo': 175,
            'percentual': round((max(0, score_total) / 175) * 100, 1),
            'classificacao': classificacao,
            'prioridade': prioridade,
            'is_vip': is_vip,
            'sentimento': sentimento,
            'breakdown': breakdown,
            'recomendacoes': recomendacoes,
            'qualificado': score_total >= self.scoring_config.get('minimo_qualificado', 40),
            'timestamp': datetime.now().isoformat()
        }
    
    
    def _score_perguntas(self, respostas: Dict) -> Tuple[int, Dict]:
        """Calcula score baseado nas respostas das perguntas"""
        score = 0
        breakdown = {}
        
        for pergunta in self.perguntas:
            pergunta_id = pergunta['id']
            campo_lead = pergunta.get('campo_lead', pergunta_id)
            resposta = respostas.get(campo_lead, '')
            
            if not resposta:
                breakdown[pergunta_id] = {'score': 0, 'motivo': 'Não respondida'}
                continue
            
            # Score específico por tipo de pergunta
            pergunta_score = 0
            motivo = ''
            
            if pergunta_id == 'nome':
                pergunta_score, motivo = self._score_nome(resposta, pergunta)
            
            elif pergunta_id == 'interesse':
                pergunta_score, motivo = self._score_interesse(resposta, pergunta)
            
            elif pergunta_id == 'orcamento':
                pergunta_score, motivo = self._score_orcamento(resposta, pergunta)
            
            elif pergunta_id == 'prazo':
                pergunta_score, motivo = self._score_prazo(resposta, pergunta)
            
            elif pergunta_id == 'contato':
                pergunta_score, motivo = self._score_contato(resposta, pergunta)
            
            elif pergunta_id == 'empresa':
                pergunta_score, motivo = self._score_empresa(resposta, pergunta)
            
            elif pergunta_id == 'tamanho_empresa':
                pergunta_score, motivo = self._score_tamanho_empresa(resposta, pergunta)
            
            else:
                # Score genérico para perguntas customizadas
                pergunta_score = 10
                motivo = 'Respondida'
            
            score += pergunta_score
            breakdown[pergunta_id] = {
                'score': pergunta_score,
                'motivo': motivo,
                'resposta': resposta[:50]  # Primeiros 50 caracteres
            }
        
        return score, breakdown
    
    
    def _score_nome(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para nome completo"""
        validacao = pergunta.get('validacao', {})
        scores = pergunta.get('score', {})
        
        # Verificar se tem nome e sobrenome
        palavras = resposta.strip().split()
        
        if len(palavras) >= validacao.get('min_palavras', 2):
            # Verificar regex (apenas letras)
            if re.match(validacao.get('regex', ''), resposta):
                return scores.get('completo', 20), 'Nome completo válido'
            else:
                return scores.get('incompleto', 5), 'Nome com caracteres inválidos'
        else:
            return scores.get('incompleto', 5), 'Nome incompleto'
    
    
    def _score_interesse(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para interesse/produto"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        
        # Keywords de alto valor
        keywords_alto = pergunta.get('keywords_alto_valor', [])
        keywords_baixo = pergunta.get('keywords_baixo_valor', [])
        
        # Verificar alto valor
        for keyword in keywords_alto:
            if keyword in resposta_lower:
                return scores.get('resposta_detalhada', 25), f'Alto valor: {keyword}'
        
        # Verificar baixo valor
        for keyword in keywords_baixo:
            if keyword in resposta_lower:
                return 5, f'Baixo valor: {keyword}'
        
        # Resposta detalhada (mais de 10 caracteres)
        if len(resposta) > 10:
            return scores.get('resposta_detalhada', 25), 'Resposta detalhada'
        else:
            return scores.get('resposta_basica', 10), 'Resposta básica'
    
    
    def _score_orcamento(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para orçamento"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        ranges = pergunta.get('ranges', {})
        
        # Tentar extrair número
        numeros = re.findall(r'\d+', resposta)
        if numeros:
            valor = int(numeros[0])
            
            # Classificar por range
            if valor >= ranges.get('premium', {}).get('min', 10000):
                return scores.get('premium', 30), f'Premium: R$ {valor:,}'
            elif valor >= ranges.get('alto', {}).get('min', 5000):
                return scores.get('alto', 25), f'Alto: R$ {valor:,}'
            elif valor >= ranges.get('medio', {}).get('min', 2000):
                return scores.get('medio', 15), f'Médio: R$ {valor:,}'
            else:
                return scores.get('baixo', 5), f'Baixo: R$ {valor:,}'
        
        # Verificar keywords
        for categoria, config in ranges.items():
            for keyword in config.get('keywords', []):
                if keyword in resposta_lower:
                    return scores.get(categoria, 10), f'{categoria.capitalize()}: {keyword}'
        
        return scores.get('nao_informado', 0), 'Orçamento não especificado'
    
    
    def _score_prazo(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para prazo/urgência"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        keywords = pergunta.get('keywords_urgencia', {})
        
        # Verificar urgência
        for nivel, palavras in keywords.items():
            for palavra in palavras:
                if palavra in resposta_lower:
                    score_nivel = scores.get(nivel, 10)
                    return score_nivel, f'Urgência: {nivel} ({palavra})'
        
        return scores.get('longo', 5), 'Prazo não definido'
    
    
    def _score_contato(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para preferência de contato"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        
        if 'whatsapp' in resposta_lower or 'zap' in resposta_lower:
            return scores.get('whatsapp', 15), 'WhatsApp'
        elif 'telefone' in resposta_lower or 'ligar' in resposta_lower:
            return scores.get('telefone', 15), 'Telefone'
        elif 'email' in resposta_lower or 'e-mail' in resposta_lower:
            return scores.get('email', 10), 'Email'
        elif 'qualquer' in resposta_lower or 'tanto faz' in resposta_lower:
            return scores.get('qualquer', 12), 'Qualquer canal'
        
        return 10, 'Preferência registrada'
    
    
    def _score_empresa(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para tipo de cliente"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        
        if 'empresa' in resposta_lower or 'negócio' in resposta_lower or 'cnpj' in resposta_lower:
            return scores.get('empresa', 20), 'Cliente empresarial'
        else:
            return scores.get('pessoal', 10), 'Cliente pessoa física'
    
    
    def _score_tamanho_empresa(self, resposta: str, pergunta: Dict) -> Tuple[int, str]:
        """Score para tamanho da empresa"""
        resposta_lower = resposta.lower()
        scores = pergunta.get('score', {})
        ranges = pergunta.get('ranges', {})
        
        # Tentar extrair número
        numeros = re.findall(r'\d+', resposta)
        if numeros:
            funcionarios = int(numeros[0])
            
            if funcionarios >= ranges.get('grande', {}).get('min', 50):
                return scores.get('grande', 30), f'Grande empresa: {funcionarios} funcionários'
            elif funcionarios >= ranges.get('media', {}).get('min', 10):
                return scores.get('media', 20), f'Média empresa: {funcionarios} funcionários'
            else:
                return scores.get('pequena', 10), f'Pequena empresa: {funcionarios} funcionários'
        
        # Verificar keywords
        for categoria, config in ranges.items():
            for keyword in config.get('keywords', []):
                if keyword in resposta_lower:
                    return scores.get(categoria, 10), f'{categoria.capitalize()} empresa'
        
        return 10, 'Tamanho não especificado'
    
    
    def _analisar_sentimento(self, historico_mensagens: List[Dict]) -> Tuple[int, str]:
        """Analisa o sentimento geral da conversa"""
        if not self.analise_sentimento.get('habilitado', False):
            return 0, 'neutro'
        
        keywords_positivos = self.analise_sentimento.get('keywords_positivos', [])
        keywords_negativos = self.analise_sentimento.get('keywords_negativos', [])
        ajustes = self.analise_sentimento.get('ajuste_score', {})
        
        score_positivo = 0
        score_negativo = 0
        
        # Analisar apenas mensagens do lead
        for msg in historico_mensagens:
            if msg.get('sender_type') != 'lead':
                continue
            
            texto = msg.get('body', '').lower()
            
            # Contar keywords positivas
            for keyword in keywords_positivos:
                if keyword in texto:
                    score_positivo += 1
            
            # Contar keywords negativas
            for keyword in keywords_negativos:
                if keyword in texto:
                    score_negativo += 1
        
        # Determinar sentimento geral
        diferenca = score_positivo - score_negativo
        
        if diferenca >= 3:
            return ajustes.get('muito_positivo', 10), 'muito_positivo'
        elif diferenca >= 1:
            return ajustes.get('positivo', 5), 'positivo'
        elif diferenca <= -3:
            return ajustes.get('muito_negativo', -10), 'muito_negativo'
        elif diferenca <= -1:
            return ajustes.get('negativo', -5), 'negativo'
        else:
            return ajustes.get('neutro', 0), 'neutro'
    
    
    def _aplicar_penalidades(self, respostas: Dict, historico_mensagens: List[Dict]) -> Tuple[int, List[str]]:
        """Aplica penalidades por comportamentos negativos"""
        penalidades = self.scoring_config.get('penalidades', {})
        penalidade_total = 0
        motivos = []
        
        # 1. Respostas evasivas (muito curtas)
        respostas_curtas = 0
        for resposta in respostas.values():
            if isinstance(resposta, str) and len(resposta) <= 3:
                respostas_curtas += 1
        
        if respostas_curtas >= 3:
            pen = penalidades.get('respostas_evasivas', -10)
            penalidade_total += pen
            motivos.append(f'Respostas evasivas ({pen} pts)')
        
        # 2. Keywords negativas
        keywords_negativas = self.config.get('keywords_negativas', [])
        count_negativas = 0
        
        for msg in historico_mensagens:
            if msg.get('sender_type') != 'lead':
                continue
            
            texto = msg.get('body', '').lower()
            for keyword in keywords_negativas:
                if keyword in texto:
                    count_negativas += 1
        
        if count_negativas > 0:
            pen = penalidades.get('keywords_negativas', -15) * count_negativas
            penalidade_total += pen
            motivos.append(f'Keywords negativas x{count_negativas} ({pen} pts)')
        
        # 3. Timeout (muitas mensagens, pouco engajamento)
        if len(historico_mensagens) > 15:
            pen = penalidades.get('timeout', -5)
            penalidade_total += pen
            motivos.append(f'Conversa muito longa ({pen} pts)')
        
        return penalidade_total, motivos
    
    
    def _classificar_lead(self, score: int, respostas: Dict) -> Tuple[str, str]:
        """
        Classifica o lead em hot/warm/cold e define prioridade
        
        Returns:
            Tuple[classificação, prioridade]
        """
        minimo_vip = self.scoring_config.get('minimo_vip', 80)
        minimo_alta = self.scoring_config.get('minimo_alta_prioridade', 60)
        minimo_qualificado = self.scoring_config.get('minimo_qualificado', 40)
        
        if score >= minimo_vip:
            return 'hot', 'vip'
        elif score >= minimo_alta:
            return 'warm', 'alta'
        elif score >= minimo_qualificado:
            return 'warm', 'normal'
        else:
            return 'cold', 'baixa'
    
    
    def _detectar_vip(self, respostas: Dict, score: int) -> bool:
        """
        Detecta se é um lead VIP baseado em critérios especiais
        além do score (orçamento alto + urgência)
        """
        # Critério 1: Score >= 80
        if score >= self.scoring_config.get('minimo_vip', 80):
            return True
        
        # Critério 2: Orçamento premium + Prazo urgente
        orcamento = str(respostas.get('orcamento', '')).lower()
        prazo = str(respostas.get('prazo', '')).lower()
        
        # Keywords de orçamento premium
        orcamento_premium = any(k in orcamento for k in ['10 mil', '20 mil', '50 mil', '100 mil', 'premium'])
        
        # Keywords de urgência
        prazo_urgente = any(k in prazo for k in ['hoje', 'agora', 'imediato', 'urgente', 'já'])
        
        if orcamento_premium and prazo_urgente:
            return True
        
        # Critério 3: Empresa grande
        tamanho = str(respostas.get('tamanho_empresa', '')).lower()
        if any(k in tamanho for k in ['50', '100', 'mais de 50', 'grande']):
            return True
        
        return False
    
    
    def _gerar_recomendacoes(self, score: int, classificacao: str, 
                            respostas: Dict, sentimento: str) -> List[str]:
        """Gera recomendações de ação baseadas na análise"""
        recomendacoes = []
        
        # Recomendações por classificação
        if classificacao == 'hot':
            recomendacoes.append('🔥 Lead HOT! Atender imediatamente')
            recomendacoes.append('Oferecer melhor vendedor disponível')
            recomendacoes.append('Preparar proposta premium')
        
        elif classificacao == 'warm':
            recomendacoes.append('⚡ Lead qualificado - atender em até 1h')
            recomendacoes.append('Enviar material complementar')
        
        else:
            recomendacoes.append('❄️ Lead frio - considerar nurturing')
            recomendacoes.append('Agendar follow-up em 24-48h')
        
        # Recomendações por sentimento
        if sentimento == 'muito_negativo':
            recomendacoes.append('⚠️ Sentimento negativo - vendedor experiente')
            recomendacoes.append('Focar em resolver objeções')
        
        elif sentimento == 'muito_positivo':
            recomendacoes.append('😊 Cliente entusiasmado - momento ideal para fechar')
        
        # Recomendações por orçamento
        orcamento = str(respostas.get('orcamento', '')).lower()
        if any(k in orcamento for k in ['barato', 'grátis', 'teste']):
            recomendacoes.append('💰 Orçamento limitado - apresentar opções básicas primeiro')
        
        # Recomendações por prazo
        prazo = str(respostas.get('prazo', '')).lower()
        if any(k in prazo for k in ['hoje', 'agora', 'urgente']):
            recomendacoes.append('⏰ URGENTE - priorizar máxima')
        
        return recomendacoes
    
    
    def verificar_fluxos_condicionais(self, respostas: Dict, score: int) -> List[Dict]:
        """
        Verifica e executa fluxos condicionais baseados em regras
        
        Returns:
            Lista de ações a executar
        """
        fluxos = self.config.get('fluxos_condicionais', {})
        if not fluxos.get('habilitado', False):
            return []
        
        regras = fluxos.get('regras', [])
        acoes = []
        
        for regra in regras:
            condicao = regra.get('se', '')
            
            # Avaliar condição (simplificado - em produção usar parser seguro)
            try:
                # Substituir variáveis
                condicao_avaliavel = condicao
                condicao_avaliavel = condicao_avaliavel.replace('orcamento', f'"{respostas.get("orcamento", "")}"')
                condicao_avaliavel = condicao_avaliavel.replace('prazo', f'"{respostas.get("prazo", "")}"')
                condicao_avaliavel = condicao_avaliavel.replace('keywords_negativas', str(len(self.config.get('keywords_negativas', []))))
                
                # Avaliar (CUIDADO: em produção, usar método mais seguro)
                if 'premium' in condicao and 'urgente' in condicao:
                    # Caso especial VIP
                    if self._detectar_vip(respostas, score):
                        acoes.append({
                            'tipo': 'notificar_gestor',
                            'prioridade': 'vip',
                            'mensagem': regra.get('mensagem_especial', ''),
                            'notificar': regra.get('notificar', 'gestor')
                        })
                
                elif 'keywords_negativas > 2' in condicao:
                    # Lead frio - recuperação
                    count_negativas = sum(1 for msg in [] for kw in self.config.get('keywords_negativas', []) if kw in str(msg).lower())
                    if count_negativas > 2:
                        acoes.append({
                            'tipo': 'enviar_recuperacao',
                            'delay_horas': regra.get('delay_horas', 24),
                            'template': regra.get('template', 'lead_frio_reengajamento')
                        })
            
            except Exception as e:
                print(f"Erro ao avaliar regra: {e}")
                continue
        
        return acoes
    
    
    def get_metricas_triagem(self):
        """
        Retorna métricas do sistema de triagem
        
        Returns:
            Dict com estatísticas de qualificação
        """
        try:
            # Métricas básicas do sistema
            metricas = {
                'sistema_ativo': True,
                'config_carregada': bool(self.config),
                'total_perguntas': len(self.config.get('perguntas_qualificacao', [])),
                'analise_sentimento_ativa': self.config.get('analise_sentimento', {}).get('habilitado', False),
                'recuperacao_leads_ativa': self.config.get('recuperacao_leads', {}).get('habilitado', False),
                'fluxos_condicionais_ativos': self.config.get('fluxos_condicionais', {}).get('habilitado', False),
                
                # Configurações de scoring
                'score_minimo_qualificado': self.scoring_config.get('minimo_qualificado', 40),
                'score_minimo_vip': self.scoring_config.get('minimo_vip', 80),
                'score_minimo_alta_prioridade': self.scoring_config.get('minimo_alta_prioridade', 60),
                'score_maximo': 175,
                
                # Breakdown de pontos possíveis por pergunta
                'pontos_por_pergunta': self._calcular_pontos_possiveis(),
                
                # Versão
                'versao': self.config.get('versao', '2.0.0')
            }
            
            return metricas
        
        except Exception as e:
            print(f"❌ Erro ao gerar métricas de triagem: {e}")
            return {
                'sistema_ativo': False,
                'erro': str(e)
            }
    
    
    def _calcular_pontos_possiveis(self):
        """
        Calcula breakdown de pontos possíveis por pergunta
        
        Returns:
            Dict com pontos máximos por categoria
        """
        breakdown = {}
        
        for pergunta in self.perguntas:
            pergunta_id = pergunta['id']
            score_config = pergunta.get('score', {})
            
            if score_config:
                # Pegar o maior score possível
                max_score = max(score_config.values()) if score_config else 0
                breakdown[pergunta_id] = max_score
        
        # Adicionar sentimento
        if self.analise_sentimento.get('habilitado', False):
            ajustes = self.analise_sentimento.get('ajuste_score', {})
            breakdown['sentimento'] = ajustes.get('muito_positivo', 10)
        
        return breakdown


# Funções auxiliares para uso externo

def classificar_lead_simples(score: int) -> Dict:
    """Classificação rápida sem instanciar classe completa"""
    if score >= 80:
        return {'classificacao': 'hot', 'prioridade': 'vip', 'cor': '#ef4444'}
    elif score >= 60:
        return {'classificacao': 'warm', 'prioridade': 'alta', 'cor': '#f59e0b'}
    elif score >= 40:
        return {'classificacao': 'warm', 'prioridade': 'normal', 'cor': '#10b981'}
    else:
        return {'classificacao': 'cold', 'prioridade': 'baixa', 'cor': '#6b7280'}


if __name__ == '__main__':
    # Teste
    triagem = TriagemInteligente()
    
    respostas_teste = {
        'name': 'João Silva Santos',
        'interesse': 'Sistema CRM premium completo para empresa',
        'orcamento': '50 mil',
        'prazo': 'urgente, preciso hoje',
        'preferencia_contato': 'WhatsApp',
        'tipo_cliente': 'Empresa',
        'tamanho_empresa': '150 funcionários'
    }
    
    historico_teste = [
        {'sender_type': 'lead', 'body': 'Adorei o sistema! Perfeito!'},
        {'sender_type': 'bot', 'body': 'Que ótimo!'},
        {'sender_type': 'lead', 'body': 'Muito interessante mesmo'}
    ]
    
    resultado = triagem.calcular_score_completo(respostas_teste, historico_teste)
    
    print("=" * 60)
    print("RESULTADO DA TRIAGEM")
    print("=" * 60)
    print(f"Score Total: {resultado['score_total']}/{resultado['score_maximo']}")
    print(f"Percentual: {resultado['percentual']}%")
    print(f"Classificação: {resultado['classificacao'].upper()}")
    print(f"Prioridade: {resultado['prioridade'].upper()}")
    print(f"VIP: {'SIM ⭐' if resultado['is_vip'] else 'NÃO'}")
    print(f"Sentimento: {resultado['sentimento']}")
    print(f"Qualificado: {'SIM ✅' if resultado['qualificado'] else 'NÃO ❌'}")
    print("\nRecomendações:")
    for rec in resultado['recomendacoes']:
        print(f"  • {rec}")
    print("=" * 60)