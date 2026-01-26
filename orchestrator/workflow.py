"""
Workflow orchestrator usando LangGraph.

Definisce il grafo di esecuzione che coordina i tre agenti:
1. Research Agent → Ricerca informazioni
2. Analysis Agent → Analizza risultati
3. Synthesis Agent → Genera report

Questo è il cuore del sistema A2A (Agent-to-Agent).
"""

import asyncio
import time
from typing import Any, Dict, Optional, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from .state import (
    WorkflowState,
    WorkflowStatus,
    create_initial_state,
    add_agent_result,
    get_state_summary
)

import sys
sys.path.append("..")
from agents import (
    create_research_agent,
    create_analysis_agent,
    create_synthesis_agent
)
from config import VERBOSE


# =============================================================================
# Node Functions (eseguite dal grafo)
# =============================================================================

async def research_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Nodo di ricerca: esegue il Research Agent.
    
    Input: query dall'utente
    Output: risultati di ricerca (web + news)
    """
    if VERBOSE:
        print(f"\n{'='*50}")
        print("🔍 FASE 1: RICERCA")
        print(f"{'='*50}")
    
    start_time = time.time()
    
    # Crea/ottieni agente
    agent = create_research_agent()
    
    # Estrai parametri
    query = state["query"]
    options = state.get("options", {})
    include_news = options.get("include_news", True)
    deep_search = options.get("deep_search", False)
    
    try:
        # Esegui ricerca
        results = await agent.research_topic(
            topic=query,
            include_news=include_news,
            deep_search=deep_search
        )
        
        duration = time.time() - start_time
        
        # Prepara risultato
        agent_result = add_agent_result(
            state=state,
            agent_id="research_agent",
            success=True,
            data={"sources_found": len(results.get("web_results", []))},
            duration=duration
        )
        
        if VERBOSE:
            print(f"✅ Ricerca completata in {duration:.1f}s")
            print(f"   - Web results: {len(results.get('web_results', []))}")
            print(f"   - News results: {len(results.get('news_results', []))}")
        
        return {
            "status": WorkflowStatus.RESEARCHING,
            "current_agent": "research_agent",
            "research_results": results,
            "agent_history": [agent_result]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Errore ricerca: {str(e)}"
        
        if VERBOSE:
            print(f"❌ {error_msg}")
        
        return {
            "status": WorkflowStatus.FAILED,
            "errors": [error_msg],
            "agent_history": [add_agent_result(
                state=state,
                agent_id="research_agent",
                success=False,
                data={},
                duration=duration,
                error=error_msg
            )]
        }


async def analysis_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Nodo di analisi: esegue l'Analysis Agent.
    
    Input: risultati dalla ricerca
    Output: analisi strutturata (entità, temi, qualità)
    """
    if VERBOSE:
        print(f"\n{'='*50}")
        print("🔬 FASE 2: ANALISI")
        print(f"{'='*50}")
    
    start_time = time.time()
    
    # Verifica prerequisiti
    research_results = state.get("research_results")
    if not research_results:
        return {
            "status": WorkflowStatus.FAILED,
            "errors": ["Nessun risultato di ricerca da analizzare"]
        }
    
    # Crea/ottieni agente
    agent = create_analysis_agent()
    
    try:
        # Analizza risultati ricerca
        analysis = await agent.analyze_research_results(research_results)
        
        duration = time.time() - start_time
        
        # Prepara risultato
        agent_result = add_agent_result(
            state=state,
            agent_id="analysis_agent",
            success=True,
            data={"themes_found": len(analysis.get("temi_principali", []))},
            duration=duration
        )
        
        if VERBOSE:
            print(f"✅ Analisi completata in {duration:.1f}s")
            sources_info = analysis.get("sources_analyzed", {})
            print(f"   - Fonti analizzate: {sources_info}")
        
        return {
            "status": WorkflowStatus.ANALYZING,
            "current_agent": "analysis_agent",
            "analysis_results": analysis,
            "agent_history": [agent_result]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Errore analisi: {str(e)}"
        
        if VERBOSE:
            print(f"❌ {error_msg}")
        
        return {
            "status": WorkflowStatus.FAILED,
            "errors": [error_msg],
            "agent_history": [add_agent_result(
                state=state,
                agent_id="analysis_agent",
                success=False,
                data={},
                duration=duration,
                error=error_msg
            )]
        }


async def synthesis_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Nodo di sintesi: esegue il Synthesis Agent.
    
    Input: risultati ricerca + analisi
    Output: report finale
    """
    if VERBOSE:
        print(f"\n{'='*50}")
        print("📝 FASE 3: SINTESI E REPORT")
        print(f"{'='*50}")
    
    start_time = time.time()
    
    # Verifica prerequisiti
    research_results = state.get("research_results", {})
    analysis_results = state.get("analysis_results", {})
    
    if not research_results:
        return {
            "status": WorkflowStatus.FAILED,
            "errors": ["Dati insufficienti per generare report"]
        }
    
    # Crea/ottieni agente
    agent = create_synthesis_agent()
    
    # Parametri
    options = state.get("options", {})
    output_format = options.get("output_format", "markdown")
    
    try:
        # Genera report
        report_result = await agent.create_report(
            topic=state["query"],
            research_data=research_results,
            analysis_data=analysis_results,
            output_format=output_format
        )
        
        duration = time.time() - start_time
        
        # Prepara risultato
        agent_result = add_agent_result(
            state=state,
            agent_id="synthesis_agent",
            success=True,
            data={
                "word_count": report_result.get("word_count", 0),
                "file_path": report_result.get("file_path", "")
            },
            duration=duration
        )
        
        if VERBOSE:
            print(f"✅ Report generato in {duration:.1f}s")
            print(f"   - Parole: {report_result.get('word_count', 0)}")
            print(f"   - File: {report_result.get('file_path', 'N/A')}")
        
        return {
            "status": WorkflowStatus.SYNTHESIZING,
            "current_agent": "synthesis_agent",
            "synthesis_results": report_result,
            "agent_history": [agent_result]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Errore sintesi: {str(e)}"
        
        if VERBOSE:
            print(f"❌ {error_msg}")
        
        return {
            "status": WorkflowStatus.FAILED,
            "errors": [error_msg],
            "agent_history": [add_agent_result(
                state=state,
                agent_id="synthesis_agent",
                success=False,
                data={},
                duration=duration,
                error=error_msg
            )]
        }


async def finalize_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Nodo finale: prepara output e chiude workflow.
    """
    if VERBOSE:
        print(f"\n{'='*50}")
        print("✨ WORKFLOW COMPLETATO")
        print(f"{'='*50}")
    
    # Prepara output finale
    final_output = {
        "task_id": state.get("task_id"),
        "query": state.get("query"),
        "status": "success",
        "summary": get_state_summary(state)
    }
    
    # Aggiungi risultati chiave
    if state.get("synthesis_results"):
        final_output["report"] = {
            "file_path": state["synthesis_results"].get("file_path"),
            "word_count": state["synthesis_results"].get("word_count"),
            "preview": state["synthesis_results"].get("report_preview", "")[:500]
        }
    
    if state.get("analysis_results"):
        final_output["insights"] = {
            "themes": state["analysis_results"].get("temi_principali", []),
            "gaps": state["analysis_results"].get("lacune", [])
        }
    
    # Calcola tempo totale
    started = datetime.fromisoformat(state["started_at"])
    total_duration = (datetime.now() - started).total_seconds()
    final_output["total_duration_seconds"] = round(total_duration, 1)
    
    if VERBOSE:
        print(f"⏱️  Durata totale: {total_duration:.1f}s")
        if "report" in final_output:
            print(f"📄 Report salvato: {final_output['report']['file_path']}")
    
    return {
        "status": WorkflowStatus.COMPLETED,
        "completed_at": datetime.now().isoformat(),
        "final_output": final_output
    }


def should_continue(state: WorkflowState) -> Literal["continue", "end"]:
    """Determina se continuare o terminare il workflow."""
    if state.get("status") == WorkflowStatus.FAILED:
        return "end"
    return "continue"


# =============================================================================
# Graph Builder
# =============================================================================

def build_workflow_graph() -> StateGraph:
    """
    Costruisce il grafo del workflow.
    
    Struttura:
    START → research → analysis → synthesis → finalize → END
    
    Con gestione errori: ogni nodo può portare a END in caso di fallimento.
    """
    
    # Crea grafo con tipo stato
    workflow = StateGraph(WorkflowState)
    
    # Aggiungi nodi
    workflow.add_node("research", research_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("finalize", finalize_node)
    
    # Definisci edge (transizioni)
    workflow.set_entry_point("research")
    
    # Research → Analysis (o END se fallito)
    workflow.add_conditional_edges(
        "research",
        should_continue,
        {
            "continue": "analysis",
            "end": END
        }
    )
    
    # Analysis → Synthesis (o END se fallito)
    workflow.add_conditional_edges(
        "analysis",
        should_continue,
        {
            "continue": "synthesis",
            "end": END
        }
    )
    
    # Synthesis → Finalize (o END se fallito)
    workflow.add_conditional_edges(
        "synthesis",
        should_continue,
        {
            "continue": "finalize",
            "end": END
        }
    )
    
    # Finalize → END
    workflow.add_edge("finalize", END)
    
    return workflow


# =============================================================================
# Main Orchestrator Class
# =============================================================================

class ResearchOrchestrator:
    """
    Orchestratore principale del sistema multi-agente.
    
    Coordina l'esecuzione del workflow completo:
    ricerca → analisi → sintesi
    
    Esempio d'uso:
        orchestrator = ResearchOrchestrator()
        result = await orchestrator.run("AI in banking 2026")
    """
    
    def __init__(self):
        """Inizializza l'orchestratore."""
        self.graph = build_workflow_graph()
        self.app = self.graph.compile()
        self._run_count = 0
    
    async def run(
        self,
        query: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Esegue il workflow completo.
        
        Args:
            query: Query/argomento da ricercare
            options: Opzioni configurazione:
                - include_news: bool (default True)
                - deep_search: bool (default False)
                - output_format: str (markdown/html)
                
        Returns:
            Risultato finale con report e insights
        """
        self._run_count += 1
        task_id = f"task_{self._run_count:04d}"
        
        if VERBOSE:
            print(f"\n{'#'*60}")
            print(f"# MULTI-AGENT RESEARCH ASSISTANT")
            print(f"# Task: {task_id}")
            print(f"# Query: {query[:50]}...")
            print(f"{'#'*60}")
        
        # Crea stato iniziale
        initial_state = create_initial_state(
            query=query,
            task_id=task_id,
            options=options or {}
        )
        
        # Esegui workflow
        try:
            final_state = await self.app.ainvoke(initial_state)
            
            # Estrai output
            if final_state.get("final_output"):
                return final_state["final_output"]
            
            # Fallback per errori
            return {
                "task_id": task_id,
                "status": "error",
                "errors": final_state.get("errors", ["Unknown error"]),
                "partial_results": {
                    "research": final_state.get("research_results"),
                    "analysis": final_state.get("analysis_results")
                }
            }
            
        except Exception as e:
            return {
                "task_id": task_id,
                "status": "error",
                "errors": [str(e)]
            }
    
    def get_graph_visualization(self) -> str:
        """Restituisce rappresentazione ASCII del grafo."""
        return """
        ┌─────────────┐
        │    START    │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │  RESEARCH   │──────────┐
        │   Agent     │          │ (error)
        └──────┬──────┘          │
               │                 ▼
               │ (success)    ┌──────┐
               ▼              │ END  │
        ┌─────────────┐       └──────┘
        │  ANALYSIS   │──────────┘
        │   Agent     │
        └──────┬──────┘
               │
               │ (success)
               ▼
        ┌─────────────┐
        │  SYNTHESIS  │──────────┘
        │   Agent     │
        └──────┬──────┘
               │
               │ (success)
               ▼
        ┌─────────────┐
        │  FINALIZE   │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │     END     │
        └─────────────┘
        """


# =============================================================================
# Convenience function
# =============================================================================

async def run_research(
    query: str,
    include_news: bool = True,
    deep_search: bool = False,
    output_format: str = "markdown"
) -> Dict[str, Any]:
    """
    Funzione di convenienza per eseguire una ricerca.
    
    Args:
        query: Argomento da ricercare
        include_news: Includere ricerca news
        deep_search: Fetch pagine per più dettagli
        output_format: Formato report (markdown/html)
        
    Returns:
        Risultati della ricerca con report
    """
    orchestrator = ResearchOrchestrator()
    
    return await orchestrator.run(
        query=query,
        options={
            "include_news": include_news,
            "deep_search": deep_search,
            "output_format": output_format
        }
    )
