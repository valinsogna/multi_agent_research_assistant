"""
Configurazione centralizzata per Multi-Agent Research Assistant.
"""

import os
from pathlib import Path
from typing import Literal

# =============================================================================
# DIRECTORIES
# =============================================================================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Crea directories se non esistono
for dir_path in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]:
    dir_path.mkdir(exist_ok=True)

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Modello Ollama da usare (cambia in base a cosa hai scaricato)
# Opzioni: "deepseek-r1:7b", "llama3.2:3b", "qwen2.5:7b", "mistral:7b"
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")

# URL del server Ollama
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Parametri di generazione
LLM_TEMPERATURE: float = 0.3  # Più basso = più deterministico
LLM_MAX_TOKENS: int = 2048
LLM_TOP_P: float = 0.9

# =============================================================================
# MCP SERVER CONFIGURATION
# =============================================================================

# Porta base per i server MCP (ogni server usa porta + offset)
MCP_BASE_PORT: int = 8100

# Timeout per chiamate MCP (secondi)
MCP_TIMEOUT: int = 30

# =============================================================================
# WEB SEARCH CONFIGURATION
# =============================================================================

# Numero massimo di risultati per ricerca
MAX_SEARCH_RESULTS: int = 10

# Timeout per richieste web (secondi)
WEB_TIMEOUT: int = 15

# User agent per requests
USER_AGENT: str = "Mozilla/5.0 (compatible; ResearchAssistant/1.0)"

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

# Numero massimo di iterazioni per agente
MAX_AGENT_ITERATIONS: int = 10

# Verbose logging
VERBOSE: bool = True

# Lingua preferita per output
OUTPUT_LANGUAGE: Literal["it", "en"] = "it"

# =============================================================================
# EMBEDDING CONFIGURATION (per RAG opzionale)
# =============================================================================

# Modello embeddings (HuggingFace)
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# Dimensione chunk per documenti
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200

# =============================================================================
# FINANCIAL APIs (opzionale)
# =============================================================================

# Alpha Vantage (free tier: 25 requests/day)
ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_llm_config() -> dict:
    """Restituisce configurazione LLM come dizionario."""
    return {
        "model": OLLAMA_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "top_p": LLM_TOP_P,
    }


def validate_ollama_connection() -> bool:
    """Verifica che Ollama sia in esecuzione."""
    import httpx
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_available_models() -> list[str]:
    """Restituisce lista modelli Ollama disponibili."""
    import httpx
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


if __name__ == "__main__":
    # Test configurazione
    from rich import print as rprint
    from rich.panel import Panel
    
    rprint(Panel.fit("🔧 Configurazione Multi-Agent Research Assistant"))
    
    rprint(f"\n[bold]LLM:[/bold]")
    rprint(f"  Modello: {OLLAMA_MODEL}")
    rprint(f"  URL: {OLLAMA_BASE_URL}")
    
    if validate_ollama_connection():
        rprint("  [green]✓ Ollama connesso[/green]")
        models = get_available_models()
        if models:
            rprint(f"  Modelli disponibili: {', '.join(models)}")
    else:
        rprint("  [red]✗ Ollama non raggiungibile[/red]")
        rprint("  [yellow]Esegui: ollama serve[/yellow]")
    
    rprint(f"\n[bold]Directories:[/bold]")
    rprint(f"  Project: {PROJECT_ROOT}")
    rprint(f"  Data: {DATA_DIR}")
    rprint(f"  Output: {OUTPUT_DIR}")
