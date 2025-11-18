"""
Provider base abstrato para LLMs
Define interface comum para diferentes provedores de IA
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseAIProvider(ABC):
    """
    Classe abstrata para providers de IA
    Permite trocar facilmente entre OpenAI, Anthropic, local models, etc.
    """

    def __init__(self, model: str = None, **kwargs):
        """
        Inicializa o provider

        Args:
            model: Nome do modelo a ser usado
            **kwargs: Configura��es adicionais espec�ficas do provider
        """
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 150,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Gera resposta baseada em hist�rico de mensagens

        Args:
            messages: Lista de mensagens no formato [{"role": "user|assistant|system", "content": "..."}]
            max_tokens: M�ximo de tokens na resposta
            temperature: Criatividade (0-1)
            **kwargs: Par�metros adicionais

        Returns:
            String com a resposta gerada
        """
        pass

    @abstractmethod
    async def extract_structured_data(
        self,
        text: str,
        schema: Dict
    ) -> Dict:
        """
        Extrai dados estruturados de texto

        Args:
            text: Texto para extrair dados
            schema: Schema JSON dos dados a extrair

        Returns:
            Dicion�rio com dados extra�dos
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict:
        """
        Retorna informa��es sobre o modelo

        Returns:
            Dicion�rio com informa��es (nome, provider, limites, etc)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifica se o provider est� funcionando

        Returns:
            True se estiver OK, False caso contr�rio
        """
        pass

    def format_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Formata mensagens para o formato do provider
        Pode ser sobrescrito por providers espec�ficos

        Args:
            messages: Mensagens no formato padr�o

        Returns:
            Mensagens no formato do provider
        """
        return messages

    def validate_response(self, response: str) -> bool:
        """
        Valida resposta gerada

        Args:
            response: Resposta a validar

        Returns:
            True se v�lida, False caso contr�rio
        """
        if not response or not response.strip():
            return False

        # Valida��es b�sicas
        if len(response) > 10000:  # Muito longo
            return False

        return True

    def get_stats(self) -> Dict:
        """
        Retorna estat�sticas de uso (opcional)

        Returns:
            Dicion�rio com estat�sticas
        """
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "config": self.config
        }
