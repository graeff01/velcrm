"""
Providers de IA para qualificacao
Suporta multiplos LLMs
"""
from .base_provider import BaseAIProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "BaseAIProvider",
    "OpenAIProvider"
]