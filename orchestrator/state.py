"""
State management per il workflow multi-agente.

Definisce la struttura dello stato condiviso tra gli agenti
durante l'esecuzione di un task.
"""

from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum
import operator


class WorkflowStatus(str, Enum):
    """Stato del workflow."""
    PENDING = "pending"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentResult(TypedDict, total=False):
    """Risultato di un agente."""
    agent_id: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str]
    timestamp: str
    duration_seconds: float


class ResearchResults(TypedDict, total=False):
    """Risultati della fase di ricerca."""
    topic: str
    web_results: List[Dict]
    news_results: List[Dict]
    deep_content: List[Dict]
    queries_used: List[str]
    analysis: Dict[str, Any]


class AnalysisResults(TypedDict, total=False):
    """Risultati della fase di analisi."""
    entities: Dict[str, List]
    themes: List[str]
    summary: str
    conflicts: List[Dict]
    gaps: List[str]
    quality_score: float


class SynthesisResults(TypedDict, total=False):
    """Risultati della fase di sintesi."""
    report_content: str
    executive_summary: str
    file_path: str
    format: str
    sections_count: int
    word_count: int


class WorkflowState(TypedDict, total=False):
    """
    Stato completo del workflow.
    
    Questo è lo stato condiviso che viene passato tra i nodi
    del grafo LangGraph. Ogni agente può leggere e modificare
    parti specifiche di questo stato.
    
    Pattern A2A: Lo stato funge da "lavagna condivisa" dove
    gli agenti depositano i loro risultati e leggono quelli
    degli altri.
    """
    # Input iniziale
    task_id: str
    query: str  # Query dell'utente
    options: Dict[str, Any]  # Opzioni aggiuntive
    
    # Stato workflow
    status: WorkflowStatus
    current_agent: str
    started_at: str
    completed_at: Optional[str]
    
    # Risultati per fase
    research_results: Optional[ResearchResults]
    analysis_results: Optional[AnalysisResults]
    synthesis_results: Optional[SynthesisResults]
    
    # Tracking
    agent_history: Annotated[List[AgentResult], operator.add]  # Accumula risultati
    errors: Annotated[List[str], operator.add]  # Accumula errori
    
    # Output finale
    final_output: Optional[Dict[str, Any]]


def create_initial_state(
    query: str,
    task_id: Optional[str] = None,
    options: Optional[Dict] = None
) -> WorkflowState:
    """
    Crea lo stato iniziale per un nuovo workflow.
    
    Args:
        query: Query/richiesta dell'utente
        task_id: ID univoco del task (generato se non fornito)
        options: Opzioni configurazione workflow
        
    Returns:
        WorkflowState inizializzato
    """
    import uuid
    
    return WorkflowState(
        task_id=task_id or str(uuid.uuid4())[:8],
        query=query,
        options=options or {},
        status=WorkflowStatus.PENDING,
        current_agent="",
        started_at=datetime.now().isoformat(),
        completed_at=None,
        research_results=None,
        analysis_results=None,
        synthesis_results=None,
        agent_history=[],
        errors=[],
        final_output=None
    )


def add_agent_result(
    state: WorkflowState,
    agent_id: str,
    success: bool,
    data: Dict[str, Any],
    duration: float,
    error: Optional[str] = None
) -> AgentResult:
    """
    Crea un record di risultato agente.
    
    Args:
        state: Stato corrente (per riferimento)
        agent_id: ID dell'agente
        success: Se l'esecuzione è andata a buon fine
        data: Dati prodotti
        duration: Durata in secondi
        error: Messaggio errore se presente
        
    Returns:
        AgentResult da aggiungere alla history
    """
    return AgentResult(
        agent_id=agent_id,
        success=success,
        data=data,
        error=error,
        timestamp=datetime.now().isoformat(),
        duration_seconds=round(duration, 2)
    )


def get_state_summary(state: WorkflowState) -> Dict[str, Any]:
    """
    Genera un summary leggibile dello stato.
    
    Args:
        state: Stato da riassumere
        
    Returns:
        Dizionario con informazioni chiave
    """
    return {
        "task_id": state.get("task_id"),
        "query": state.get("query", "")[:100],
        "status": state.get("status", WorkflowStatus.PENDING).value,
        "current_agent": state.get("current_agent", ""),
        "agents_completed": len(state.get("agent_history", [])),
        "errors_count": len(state.get("errors", [])),
        "has_research": state.get("research_results") is not None,
        "has_analysis": state.get("analysis_results") is not None,
        "has_synthesis": state.get("synthesis_results") is not None,
        "started_at": state.get("started_at"),
        "completed_at": state.get("completed_at")
    }
