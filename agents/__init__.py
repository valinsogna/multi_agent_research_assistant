"""
Agents package.

Contiene gli agenti specializzati:
- ResearchAgent: Ricerca informazioni web/news
- AnalysisAgent: Analisi documenti e dati
- SynthesisAgent: Generazione report e sintesi
"""

from .base_agent import (
    BaseAgent,
    AgentMessage,
    MessageType,
    AgentCapability,
    AgentRegistry,
    get_registry
)
from .research_agent import ResearchAgent, create_research_agent
from .analysis_agent import AnalysisAgent, create_analysis_agent
from .synthesis_agent import SynthesisAgent, create_synthesis_agent

__all__ = [
    # Base
    "BaseAgent",
    "AgentMessage",
    "MessageType",
    "AgentCapability",
    "AgentRegistry",
    "get_registry",
    # Agents
    "ResearchAgent",
    "AnalysisAgent",
    "SynthesisAgent",
    # Factories
    "create_research_agent",
    "create_analysis_agent",
    "create_synthesis_agent",
]
