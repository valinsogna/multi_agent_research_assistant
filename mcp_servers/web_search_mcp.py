"""
MCP Server per Web Search usando DuckDuckGo.

Questo server espone tool per:
- Ricerca web generica
- Ricerca news
- Fetch contenuto pagina

Segue le best practices MCP di Anthropic.
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, List
from enum import Enum

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
import httpx
from duckduckgo_search import DDGS

# =============================================================================
# Server Initialization
# =============================================================================

mcp = FastMCP("web_search_mcp")

# =============================================================================
# Pydantic Models (Input Validation)
# =============================================================================

class ResponseFormat(str, Enum):
    """Formato output."""
    MARKDOWN = "markdown"
    JSON = "json"


class WebSearchInput(BaseModel):
    """Input per ricerca web generica."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    query: str = Field(
        ..., 
        description="Query di ricerca (es. 'AI in banking 2024')",
        min_length=2,
        max_length=500
    )
    max_results: int = Field(
        default=10,
        description="Numero massimo di risultati",
        ge=1,
        le=50
    )
    region: str = Field(
        default="it-it",
        description="Regione per i risultati (es. 'it-it', 'en-us')"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output: 'markdown' o 'json'"
    )


class NewsSearchInput(BaseModel):
    """Input per ricerca news."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    query: str = Field(
        ...,
        description="Query per ricerca news",
        min_length=2,
        max_length=500
    )
    max_results: int = Field(
        default=10,
        description="Numero massimo di risultati",
        ge=1,
        le=50
    )
    timelimit: Optional[str] = Field(
        default="w",
        description="Filtro temporale: 'd' (giorno), 'w' (settimana), 'm' (mese)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class FetchPageInput(BaseModel):
    """Input per fetch pagina web."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    url: str = Field(
        ...,
        description="URL completo della pagina da recuperare",
        pattern=r"^https?://"
    )
    extract_text: bool = Field(
        default=True,
        description="Se True, estrae solo il testo (rimuove HTML)"
    )
    max_length: int = Field(
        default=5000,
        description="Lunghezza massima del contenuto estratto",
        ge=100,
        le=50000
    )


# =============================================================================
# Helper Functions
# =============================================================================

def format_search_results_markdown(results: List[dict], query: str) -> str:
    """Formatta risultati di ricerca in Markdown."""
    if not results:
        return f"## Nessun risultato per: {query}\n\nProva con termini diversi."
    
    output = [f"## Risultati per: {query}\n"]
    output.append(f"*{len(results)} risultati trovati*\n")
    
    for i, r in enumerate(results, 1):
        title = r.get("title", "Senza titolo")
        url = r.get("href", r.get("link", "#"))
        snippet = r.get("body", r.get("snippet", ""))
        
        output.append(f"### {i}. {title}")
        output.append(f"🔗 {url}")
        if snippet:
            output.append(f"\n{snippet}\n")
        output.append("")
    
    return "\n".join(output)


def format_news_results_markdown(results: List[dict], query: str) -> str:
    """Formatta risultati news in Markdown."""
    if not results:
        return f"## Nessuna news per: {query}\n"
    
    output = [f"## 📰 News: {query}\n"]
    output.append(f"*{len(results)} articoli trovati*\n")
    
    for i, r in enumerate(results, 1):
        title = r.get("title", "Senza titolo")
        url = r.get("url", r.get("link", "#"))
        date = r.get("date", "")
        source = r.get("source", "")
        snippet = r.get("body", "")
        
        output.append(f"### {i}. {title}")
        if source or date:
            meta = " | ".join(filter(None, [source, date]))
            output.append(f"*{meta}*")
        output.append(f"🔗 {url}")
        if snippet:
            output.append(f"\n{snippet}\n")
        output.append("")
    
    return "\n".join(output)


async def extract_page_text(url: str, max_length: int = 5000) -> str:
    """Estrae testo da una pagina web."""
    from bs4 import BeautifulSoup
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ResearchAssistant/1.0)"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # Rimuovi script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # Estrai testo
        text = soup.get_text(separator="\n", strip=True)
        
        # Pulisci linee vuote multiple
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        # Tronca se necessario
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[... contenuto troncato ...]"
        
        return text


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool(
    name="web_search_query",
    annotations={
        "title": "Web Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def web_search_query(params: WebSearchInput) -> str:
    """
    Esegue una ricerca web usando DuckDuckGo.
    
    Utile per trovare informazioni generali, documenti, articoli.
    Restituisce titolo, URL e snippet per ogni risultato.
    
    Args:
        params: WebSearchInput con query, max_results, region, response_format
    
    Returns:
        Risultati di ricerca in formato markdown o JSON
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                params.query,
                region=params.region,
                max_results=params.max_results
            ))
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "query": params.query,
                "count": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False)
        else:
            return format_search_results_markdown(results, params.query)
            
    except Exception as e:
        error_msg = f"Errore durante la ricerca: {str(e)}"
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"error": error_msg, "query": params.query})
        return f"## ❌ Errore\n\n{error_msg}"


@mcp.tool(
    name="web_search_news",
    annotations={
        "title": "News Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def web_search_news(params: NewsSearchInput) -> str:
    """
    Cerca news recenti usando DuckDuckGo News.
    
    Ideale per trovare articoli di attualità, comunicati stampa,
    aggiornamenti di mercato.
    
    Args:
        params: NewsSearchInput con query, max_results, timelimit
    
    Returns:
        News in formato markdown o JSON con titolo, fonte, data, URL
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(
                params.query,
                max_results=params.max_results,
                timelimit=params.timelimit
            ))
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "query": params.query,
                "count": len(results),
                "timelimit": params.timelimit,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False)
        else:
            return format_news_results_markdown(results, params.query)
            
    except Exception as e:
        error_msg = f"Errore durante la ricerca news: {str(e)}"
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"error": error_msg, "query": params.query})
        return f"## ❌ Errore\n\n{error_msg}"


@mcp.tool(
    name="web_search_fetch_page",
    annotations={
        "title": "Fetch Web Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def web_search_fetch_page(params: FetchPageInput) -> str:
    """
    Recupera e estrae il contenuto di una pagina web.
    
    Utile per leggere articoli completi, documentazione,
    report disponibili online.
    
    Args:
        params: FetchPageInput con url, extract_text, max_length
    
    Returns:
        Contenuto della pagina (testo estratto o HTML)
    """
    try:
        if params.extract_text:
            content = await extract_page_text(params.url, params.max_length)
            return f"## Contenuto da: {params.url}\n\n{content}"
        else:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                response = await client.get(params.url)
                response.raise_for_status()
                html = response.text[:params.max_length]
                return f"## HTML da: {params.url}\n\n```html\n{html}\n```"
                
    except httpx.HTTPStatusError as e:
        return f"## ❌ Errore HTTP {e.response.status_code}\n\nImpossibile accedere a: {params.url}"
    except Exception as e:
        return f"## ❌ Errore\n\n{str(e)}"


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Avvia server MCP con stdio transport (per uso locale)
    mcp.run()
