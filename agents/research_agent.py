"""
Research Agent - Agente specializzato nella ricerca di informazioni.

Responsabilità:
- Ricerca web (DuckDuckGo)
- Ricerca news
- Ranking e filtraggio fonti
- Estrazione contenuti rilevanti
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_agent import (
    BaseAgent, 
    AgentMessage, 
    MessageType, 
    AgentCapability,
    get_registry
)


RESEARCH_AGENT_PROMPT = """Sei un Research Agent specializzato nella ricerca di informazioni.

Il tuo ruolo è:
1. Formulare query di ricerca efficaci
2. Analizzare i risultati e identificare le fonti più rilevanti
3. Estrarre informazioni chiave
4. Valutare l'affidabilità delle fonti

Quando analizzi risultati di ricerca:
- Identifica i punti chiave
- Valuta la rilevanza (0-1)
- Nota eventuali lacune informative
- Segnala fonti contrastanti

Rispondi in italiano. Sii conciso ma completo.
"""


class ResearchAgent(BaseAgent):
    """Agente specializzato nella ricerca di informazioni."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(
            agent_id="research_agent",
            name="Research Agent",
            description="Ricerca e raccolta informazioni da fonti web",
            system_prompt=RESEARCH_AGENT_PROMPT,
            model=model
        )
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="web_search",
                description="Ricerca informazioni sul web",
                input_schema={"topic": "str", "include_news": "bool"},
                output_schema={"results": "list", "summary": "str"}
            ),
            AgentCapability(
                name="news_search",
                description="Ricerca news recenti",
                input_schema={"topic": "str", "days": "int"},
                output_schema={"articles": "list"}
            )
        ]
    
    async def process_request(self, request: AgentMessage) -> AgentMessage:
        """Processa richieste di ricerca."""
        self.log(f"Ricevuta richiesta: {request.message_type.value}")
        
        content = request.content
        action = content.get("action", "search")
        topic = content.get("topic", "")
        
        if action == "search":
            results = await self.research_topic(
                topic=topic,
                include_news=content.get("include_news", True),
                deep_search=content.get("deep_search", False)
            )
            
            return self.create_response(
                original_request=request,
                content={"results": results},
                success=True
            )
        
        return self.create_response(
            original_request=request,
            content={"error": f"Azione non supportata: {action}"},
            success=False
        )
    
    async def _web_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Esegue ricerca web via DuckDuckGo."""
        from duckduckgo_search import DDGS
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            self.log(f"Errore web search: {e}", "ERROR")
            return []
    
    async def _news_search(self, query: str, max_results: int = 10, timelimit: str = "w") -> List[Dict]:
        """Cerca news recenti."""
        from duckduckgo_search import DDGS
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=max_results, timelimit=timelimit))
            return results
        except Exception as e:
            self.log(f"Errore news search: {e}", "ERROR")
            return []
    
    async def _fetch_page(self, url: str) -> str:
        """Recupera contenuto pagina web."""
        import httpx
        from bs4 import BeautifulSoup
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                
                text = soup.get_text(separator="\n", strip=True)
                return text[:10000]
                
        except Exception as e:
            self.log(f"Errore fetch: {e}", "ERROR")
            return ""
    
    async def research_topic(
        self,
        topic: str,
        include_news: bool = True,
        deep_search: bool = False
    ) -> Dict[str, Any]:
        """
        Ricerca completa su un argomento.
        
        Args:
            topic: Argomento da ricercare
            include_news: Includere news
            deep_search: Fetch pagine per più dettagli
            
        Returns:
            Risultati strutturati
        """
        self.log(f"Avvio ricerca: {topic}")
        
        results = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "web_results": [],
            "news_results": [],
            "deep_content": [],
            "queries_used": []
        }
        
        # Genera query
        queries = [
            topic,
            f"{topic} 2024",
            f"{topic} analisi"
        ]
        results["queries_used"] = queries
        
        # Ricerca web
        for query in queries[:2]:
            self.log(f"Query: {query}")
            web_results = await self._web_search(query, max_results=5)
            results["web_results"].extend(web_results)
        
        # Ricerca news
        if include_news:
            self.log("Ricerca news...")
            news_results = await self._news_search(topic, max_results=5)
            results["news_results"] = news_results
        
        # Deep search
        if deep_search and results["web_results"]:
            self.log("Deep search...")
            for r in results["web_results"][:2]:
                url = r.get("href", r.get("link"))
                if url:
                    content = await self._fetch_page(url)
                    if content:
                        results["deep_content"].append({
                            "url": url,
                            "content": content[:3000]
                        })
        
        # Analisi LLM
        analysis = await self._analyze_with_llm(topic, results)
        results["analysis"] = analysis
        
        return results
    
    async def _analyze_with_llm(self, topic: str, results: Dict) -> Dict[str, Any]:
        """Analizza risultati con LLM."""
        
        # Prepara contesto
        context_parts = [f"Topic: {topic}\n"]
        
        context_parts.append("## Risultati Web:")
        for i, r in enumerate(results["web_results"][:5], 1):
            title = r.get("title", "N/A")
            snippet = r.get("body", r.get("snippet", ""))[:200]
            context_parts.append(f"{i}. {title}: {snippet}")
        
        if results["news_results"]:
            context_parts.append("\n## News:")
            for i, r in enumerate(results["news_results"][:3], 1):
                title = r.get("title", "N/A")
                source = r.get("source", "")
                context_parts.append(f"{i}. [{source}] {title}")
        
        context = "\n".join(context_parts)
        
        prompt = """Analizza questi risultati di ricerca e fornisci:
1. Un riassunto dei punti principali (3-5 frasi)
2. Le fonti più rilevanti (max 3)
3. Eventuali lacune informative
4. Un punteggio di confidenza (0-1)

Rispondi in formato JSON."""

        try:
            response = await self.invoke_llm(prompt, context)
            
            # Prova a parsare come JSON
            try:
                # Cerca JSON nella risposta
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
            
            # Fallback: restituisci come testo
            return {
                "summary": response,
                "confidence": 0.7,
                "sources": [],
                "gaps": []
            }
            
        except Exception as e:
            self.log(f"Errore analisi LLM: {e}", "ERROR")
            return {
                "summary": "Analisi non disponibile",
                "confidence": 0.0,
                "error": str(e)
            }


# Factory function
def create_research_agent(model: Optional[str] = None) -> ResearchAgent:
    """Crea e registra un Research Agent."""
    agent = ResearchAgent(model=model)
    get_registry().register(agent)
    return agent
