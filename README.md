# 🔬 Multi-Agent Research Assistant

Un sistema multi-agente con protoclli **MCP** (Model Context Protocol) per eseguire ricerche web, analizzare documenti e generare report sintetici usando modelli di linguaggio locali (es. DeepSeek via Ollama).

## 🎯 Technolgie

| Requisito | Come |
|---------------------|---------------------|
| Agentic System design | 3 agenti specializzati che collaborano |
| MCP experience | Server MCP custom per web search e file analysis |
| A2A understanding | Protocollo di comunicazione tra agenti |
| GenAI technologies | DeepSeek/Llama locale via Ollama |
| Testing agentic systems | Framework di valutazione incluso |
| LangChain/LlamaIndex | Orchestrazione con LangGraph |

## 🏗️ Architettura

> 📖 Per documentazione dettagliata vedi [Q&As/ARCHITECTURE.md](./Q&As/ARCHITECTURE.md)

### Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATOR                             │
│                   (Codice Python deterministico)                        │
│                                                                         │
│   Responsabilità:                                                       │
│   • Esegue i nodi in sequenza                                           │
│   • Gestisce lo stato condiviso                                         │
│   • Decide quando fermarsi (errore/successo)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                         Flusso SEQUENZIALE
                                    │
      ┌─────────────────────────────┼─────────────────────────────┐
      │                             │                             │
      ▼                             ▼                             ▼
┌───────────┐                ┌───────────┐                ┌───────────┐
│  STEP 1   │                │  STEP 2   │                │  STEP 3   │
│ RESEARCH  │ ────────────►  │ ANALYSIS  │ ────────────►  │ SYNTHESIS │
│  AGENT    │                │   AGENT   │                │   AGENT   │
└───────────┘                └───────────┘                └───────────┘
      │                             │                             │
      ▼                             ▼                             ▼
  Trova info                  Struttura                      Genera
  (web + news)                i dati                        report
```

### Dettaglio Agenti

| Agente | Responsabilità | Input | Output | Chiamate LLM |
|--------|---------------|-------|--------|--------------|
| **🔍 Research** | Cercare informazioni grezze | Query utente | 10 web results + 5 news | 1 |
| **🔬 Analysis** | Estrarre pattern e insight | research_results (troncato) | JSON con temi, trend, lacune | 1 |
| **📝 Synthesis** | Creare report professionale | research + analysis results | File Markdown/HTML | 2 |

### Flusso Dati e Protezione Context Window

```
USER INPUT: "AI nel settore bancario"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ RESEARCH AGENT                                                          │
│                                                                         │
│ • Genera 3 varianti query: 2 di default e 1 opzionale.                  │    
│ • Web search: 2 query di default × 5 risultati = 10 totali              │
│ • News search: 5 risultati (ultima settimana)                           │
│ • 1 chiamata LLM per analisi preliminare                                │
│                                                                         │
│ OUTPUT: ~10 web results + 5 news + analisi preliminare                  │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    │  ⚠️ TRONCAMENTO (protezione context window)
                    │  • Max 5 web results (di 10)
                    │  • Max 200 char per fonte
                    │  • Max 3 news (di 5)
                    │  • TOTALE: ~3000 char (~800 token)
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ANALYSIS AGENT                                                          │
│                                                                         │
│ • Riceve dati TRONCATI (non tutto l'output di Research)                │
│ • 1 chiamata LLM con prompt strutturato                                │
│ • Output: JSON con temi, trend, lacune, contraddizioni                 │
│                                                                         │
│ OUTPUT: { temi: [...], trend: "...", lacune: [...] }                   │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ SYNTHESIS AGENT                                                         │
│                                                                         │
│ • Riceve research_results + analysis_results                           │
│ • 2 chiamate LLM: sezioni + executive summary                          │
│ • Assembla report con indice, fonti, metadata                          │
│ • Salva file in outputs/                                               │
│                                                                         │
│ OUTPUT: outputs/report_xxx.md                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Comunicazione tra Agenti (Pattern Blackboard)

Gli agenti **NON comunicano direttamente**. Leggono/scrivono su uno stato condiviso:

```python
# WorkflowState - la "lavagna" condivisa
{
    "query": "AI settore bancario",           # Input utente
    "research_results": {...},                 # ← Scritto da Research Agent
    "analysis_results": {...},                 # ← Scritto da Analysis Agent
    "synthesis_results": {...},                # ← Scritto da Synthesis Agent
    "status": "COMPLETED",
    "agent_history": [...]                     # Log esecuzione
}
```

Ogni agente:
- ✅ LEGGE dallo stato ciò che gli serve
- ✅ SCRIVE nello stato il suo output
- ❌ NON parla direttamente con altri agenti
- ❌ NON mantiene memoria delle chiamate precedenti

---

## 📋 Prerequisiti

- Python 3.10+
- 8GB+ RAM (per modelli locali)
- ~10GB spazio disco (per Ollama + modelli)

---

## 🚀 Setup Completo

### Step 1: Installa Ollama (per LLM locale)

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows: scarica da https://ollama.com/download
```

### Step 2: Scarica DeepSeek (o alternativa)

```bash
# Opzione 1: DeepSeek R1 (consigliato, ~4GB)
ollama pull deepseek-r1:7b

# Opzione 2: Llama 3.2 (più leggero, ~2GB)
ollama pull llama3.2:3b

# Opzione 3: Qwen 2.5 (buon bilanciamento)
ollama pull qwen2.5:7b

# Verifica che funzioni
ollama run deepseek-r1:7b "Ciao, rispondi brevemente"
```

### Step 3: Crea l'ambiente Conda

```bash
# Crea ambiente
conda create -n aissistant python=3.11 -y

# Attiva
conda activate aissistant
```

### Step 4: Installa le dipendenze

```bash
# Clona/entra nella cartella del progetto
cd multi_agent_research_assistant

# Installa tutto
pip install -r requirements.txt
```

---

## 📦 Struttura del Progetto

```
multi_agent_research_assistant/
├── README.md                    # Questa guida
├── requirements.txt             # Dipendenze Python
├── config.py                    # Configurazione centralizzata
│
├── mcp_servers/                 # Server MCP (Tool)
│   ├── __init__.py
│   ├── web_search_mcp.py       # Tool per ricerca web
│   ├── file_reader_mcp.py      # Tool per leggere documenti
│   └── report_writer_mcp.py    # Tool per generare report
│
├── agents/                      # Agenti specializzati
│   ├── __init__.py
│   ├── base_agent.py           # Classe base
│   ├── research_agent.py       # Agente ricerca
│   ├── analysis_agent.py       # Agente analisi
│   └── synthesis_agent.py      # Agente sintesi
│
├── orchestrator/                # Coordinamento A2A
│   ├── __init__.py
│   ├── workflow.py             # LangGraph workflow
│   └── state.py                # Stato condiviso
│
├── tests/                       # Test e valutazione
│   ├── test_mcp_servers.py
│   ├── test_agents.py
│   └── evaluation.py
│
└── examples/                    # Esempi d'uso
    ├── financial_research.py   # Caso d'uso bancario
    └── market_analysis.py      # Analisi di mercato
```

---

## 🏃 Quick Start

```bash
# 1. Attiva ambiente
conda activate aissistant

# 2. Avvia Ollama (in un terminale separato)
ollama serve

# 3. Esegui esempio
python examples/financial_research.py
```

---

## 💡 Punti da Evidenziare

1. **Design Pattern A2A**: Gli agenti comunicano tramite uno stato condiviso tipizzato
2. **MCP Standard**: I tool seguono il protocollo MCP ufficiale di Anthropic
3. **Scalabilità**: Architettura modulare, facile aggiungere nuovi agenti/tool
4. **Testing**: Framework di valutazione per misurare performance
5. **Local-First**: Funziona senza API costose (DeepSeek locale)
6. **Enterprise-Ready**: Pattern applicabili a use case bancari

---

## 📚 Documentazione Aggiuntiva

- [MCP Protocol](https://modelcontextprotocol.io/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Ollama](https://ollama.com/)
- [DeepSeek](https://deepseek.com/)
