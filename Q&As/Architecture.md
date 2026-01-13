# 🏗️ Architettura del Sistema

## Overview

Il sistema è composto da **3 agenti specializzati** coordinati da un **orchestratore LangGraph**. Gli agenti non comunicano direttamente tra loro, ma attraverso uno **stato condiviso** (pattern "blackboard").

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LANGGRAPH ORCHESTRATOR                          │
│                     (Codice Python, NON un LLM)                         │
│                                                                         │
│   • Definisce l'ordine di esecuzione                                    │
│   • Gestisce lo stato condiviso (WorkflowState)                         │
│   • Decide quando fermarsi (errori/successo)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Esecuzione SEQUENZIALE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW STATE                                │
│                    (La "lavagna" condivisa)                             │
│                                                                         │
│   {                                                                     │
│     query: "AI nel settore bancario",                                   │
│     research_results: {...},    ← Scritto da Research Agent             │
│     analysis_results: {...},    ← Scritto da Analysis Agent             │
│     synthesis_results: {...},   ← Scritto da Synthesis Agent            │
│     status: "COMPLETED",                                                │
│     agent_history: [...]                                                │
│   }                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   RESEARCH    │    ──►    │   ANALYSIS    │    ──►    │   SYNTHESIS   │
│     AGENT     │           │     AGENT     │           │     AGENT     │
└───────────────┘           └───────────────┘           └───────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  DuckDuckGo   │           │   LLM Only    │           │  File System  │
│     API       │           │ (no external) │           │   + LLM       │
└───────────────┘           └───────────────┘           └───────────────┘
```

---

## Flusso di Esecuzione

```
INPUT                                                               OUTPUT
  │                                                                   ▲
  │ "AI nel settore bancario"                                         │
  ▼                                                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 1: RESEARCH                                                         │
│                                                                          │
│ Input:  query (stringa)                                                  │
│ Output: research_results (web + news + analisi preliminare)              │
│ Tempo:  ~10-20 sec                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              │ research_results (~10 fonti)
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 2: ANALYSIS                                                         │
│                                                                          │
│ Input:  research_results (troncato: max 5 web + 3 news)                  │
│ Output: analysis_results (temi, trend, lacune, contraddizioni)           │
│ Tempo:  ~10-15 sec                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              │ analysis_results (JSON strutturato)
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 3: SYNTHESIS                                                        │
│                                                                          │
│ Input:  research_results + analysis_results                              │
│ Output: Report Markdown/HTML salvato su file                             │
│ Tempo:  ~15-20 sec                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      report_xxx.md
```

---

## Dettaglio Agenti

### 🔍 RESEARCH AGENT

**Responsabilità:** Trovare informazioni grezze da fonti web.

**System Prompt:**
```
Sei un Research Agent specializzato nella ricerca di informazioni.

Il tuo ruolo è:
1. Formulare query di ricerca efficaci
2. Analizzare i risultati e identificare le fonti più rilevanti
3. Estrarre informazioni chiave
4. Valutare l'affidabilità delle fonti

Rispondi in italiano. Sii conciso ma completo.
```

**Cosa FA:**
| Azione | Dettaglio |
|--------|-----------|
| Genera query | 3 varianti della query utente |
| Web search | DuckDuckGo, max 5 risultati × 2 query |
| News search | Ultime news (7 giorni), max 5 risultati |
| Deep search | (Opzionale) Fetch HTML top 2 pagine |
| Analisi preliminare | Chiede al LLM un primo riassunto |

**Cosa NON fa:**
- ❌ Non estrae entità strutturate
- ❌ Non identifica contraddizioni
- ❌ Non scrive report

**Input/Output:**
```
INPUT:  "AI nel settore bancario Italia"
        │
        ▼
┌─────────────────────────────────────┐
│         RESEARCH AGENT              │
│                                     │
│  1. Query generate:                 │
│     • "AI settore bancario Italia"  │
│     • "AI settore bancario 2024"    │
│     • "AI settore bancario analisi" │
│                                     │
│  2. Web search (DuckDuckGo)         │
│     • 2 query × 5 risultati = 10    │
│                                     │
│  3. News search                     │
│     • 5 news ultima settimana       │
│                                     │
│  4. LLM analysis (1 chiamata)       │
│     • Riassunto preliminare         │
└─────────────────────────────────────┘
        │
        ▼
OUTPUT: {
          "topic": "...",
          "web_results": [10 items],
          "news_results": [5 items],
          "analysis": { "summary": "...", "confidence": 0.7 }
        }
```

---

### 🔬 ANALYSIS AGENT

**Responsabilità:** Analizzare e strutturare i dati grezzi.

**System Prompt:**
```
Sei un Analysis Agent specializzato nell'analisi di documenti e dati.

Il tuo ruolo è:
1. Estrarre informazioni strutturate da documenti
2. Identificare entità chiave (aziende, persone, date, numeri)
3. Verificare coerenza tra fonti diverse
4. Evidenziare inconsistenze o dati mancanti

Rispondi in italiano. Sii preciso e metodico.
```

**Cosa FA:**
| Azione | Dettaglio |
|--------|-----------|
| Identifica temi | 3-5 temi principali ricorrenti |
| Valuta fonti | Quali sono più autorevoli |
| Trova contraddizioni | Info contrastanti tra fonti |
| Identifica trend | Pattern comune emergente |
| Nota lacune | Cosa manca nei dati |

**Cosa NON fa:**
- ❌ Non cerca nuove informazioni
- ❌ Non scrive report leggibili
- ❌ Non salva file

**Input/Output:**
```
INPUT:  research_results (TRONCATO!)
        │
        │  ⚠️ PROTEZIONE CONTEXT WINDOW:
        │  • Max 5 web results (di 10)
        │  • Max 200 char per snippet
        │  • Max 3 news (di 5)
        │  • Max 1000 char per deep content
        │  • TOTALE: ~3000 char (~800 token)
        │
        ▼
┌─────────────────────────────────────┐
│         ANALYSIS AGENT              │
│                                     │
│  1. Prepara contesto troncato       │
│                                     │
│  2. UNA chiamata LLM con prompt:    │
│     "Analizza e fornisci:           │
│      - Temi principali              │
│      - Fonti affidabili             │
│      - Contraddizioni               │
│      - Trend                        │
│      - Lacune                       │
│      Rispondi in JSON"              │
│                                     │
│  3. Parse JSON risposta             │
└─────────────────────────────────────┘
        │
        ▼
OUTPUT: {
          "temi_principali": ["AI", "Digital Banking", ...],
          "fonti_affidabili": ["Banca d'Italia", ...],
          "contraddizioni": ["..."],
          "trend": "Accelerazione investimenti",
          "lacune": ["Mancano dati ROI", ...],
          "sources_analyzed": { "web": 10, "news": 5 }
        }
```

---

### 📝 SYNTHESIS AGENT

**Responsabilità:** Creare report professionale e leggibile.

**System Prompt:**
```
Sei un Synthesis Agent specializzato nella creazione di report e documenti.

Il tuo ruolo è:
1. Combinare informazioni da fonti multiple in modo coerente
2. Creare report professionali e ben strutturati
3. Generare executive summary efficaci
4. Gestire citazioni e riferimenti appropriatamente

Rispondi in italiano. Produci contenuti di alta qualità.
```

**Cosa FA:**
| Azione | Dettaglio |
|--------|-----------|
| Genera sezioni | 4-5 sezioni del report |
| Executive summary | Riassunto 150-200 parole |
| Assembla report | Markdown o HTML formattato |
| Aggiunge fonti | Lista con link cliccabili |
| Salva file | In `outputs/report_xxx.md` |

**Cosa NON fa:**
- ❌ Non cerca informazioni
- ❌ Non analizza dati (usa analisi già fatta)
- ❌ Non prende decisioni sui contenuti

**Input/Output:**
```
INPUT:  research_results + analysis_results
        │
        ▼
┌─────────────────────────────────────┐
│         SYNTHESIS AGENT             │
│                                     │
│  1. Prepara contesto combinato      │
│                                     │
│  2. Chiamata LLM #1:                │
│     "Genera 4-5 sezioni report"     │
│                                     │
│  3. Chiamata LLM #2:                │
│     "Genera executive summary"      │
│                                     │
│  4. Assembla documento              │
│     • Header + metadata             │
│     • Summary                       │
│     • Indice                        │
│     • Sezioni                       │
│     • Fonti                         │
│                                     │
│  5. Salva su file                   │
└─────────────────────────────────────┘
        │
        ▼
OUTPUT: {
          "file_path": "outputs/report_xxx.md",
          "word_count": 1500,
          "sections_count": 5,
          "report_preview": "# Report..."
        }
```

---

## Protezioni Context Window

Ogni agente ha **limiti fissi** per evitare di superare la context window del LLM:

```
┌────────────────────────────────────────────────────────────────────────┐
│                    LIMITI PER OGNI PASSAGGIO                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  RESEARCH → ANALYSIS:                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ web_results:   10 disponibili → 5 usati (max 200 char/snippet)  │ │
│  │ news_results:   5 disponibili → 3 usati                         │ │
│  │ deep_content:   2 disponibili → 2 usati (max 1000 char/pagina)  │ │
│  │                                                                  │ │
│  │ TOTALE CONTESTO: ~3.000 caratteri (~800 token)                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ANALYSIS → SYNTHESIS:                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ research_results: passato troncato (~800 token)                 │ │
│  │ analysis_results: JSON strutturato (~500 token)                 │ │
│  │                                                                  │ │
│  │ TOTALE CONTESTO: ~1.500 token                                   │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  COMPATIBILITÀ MODELLI:                                                │
│                                                                        │
│  • Llama 3.2 3B (4K context):    ✅ OK (~1500 token usati)            │
│  • DeepSeek R1 7B (8K context):  ✅ OK                                 │
│  • GPT-4 (128K context):         ✅ OK (molto margine)                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Chiamate LLM per Agente

Ogni agente fa **chiamate LLM indipendenti** - non c'è memoria condivisa:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ RESEARCH AGENT                                                          │
│ • Chiamate LLM: 1                                                       │
│ • Scopo: Analisi preliminare dei risultati di ricerca                   │
│ • Token stimati: ~1.000                                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ ANALYSIS AGENT                                                          │
│ • Chiamate LLM: 1                                                       │
│ • Scopo: Estrarre temi, trend, lacune in formato JSON                   │
│ • Token stimati: ~1.100                                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SYNTHESIS AGENT                                                         │
│ • Chiamate LLM: 2                                                       │
│ • Scopo #1: Generare sezioni del report                                 │
│ • Scopo #2: Generare executive summary                                  │
│ • Token stimati: ~1.600                                                 │
└─────────────────────────────────────────────────────────────────────────┘

TOTALE: 4 chiamate LLM per workflow completo
        ~3.700 token input totali
        ~2.000 token output totali
```

---

## Pattern di Comunicazione

Gli agenti **NON comunicano direttamente**. Usano il pattern "Blackboard":

```
                    WORKFLOW STATE (Blackboard)
                    ┌─────────────────────────┐
                    │                         │
  Research Agent ───┼──► research_results     │
                    │                         │
                    │    research_results ────┼──► Analysis Agent
  Analysis Agent ───┼──► analysis_results     │
                    │                         │
                    │    research_results ────┼──► Synthesis Agent
                    │    analysis_results ────┼──► Synthesis Agent
  Synthesis Agent ──┼──► synthesis_results    │
                    │                         │
                    └─────────────────────────┘

NOTA: Ogni agente:
  • LEGGE dallo stato ciò che gli serve
  • SCRIVE nello stato il suo output
  • NON parla direttamente con altri agenti
  • NON mantiene memoria delle chiamate precedenti
```

---

## MCP Tool Servers

I server MCP sono **separati dagli agenti** e forniscono capacità specifiche:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP SERVERS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ WEB_SEARCH_MCP                                                  │   │
│  │                                                                  │   │
│  │ Tools:                                                          │   │
│  │ • web_search_query    → Ricerca web generica                    │   │
│  │ • web_search_news     → Ricerca news recenti                    │   │
│  │ • web_search_fetch    → Scarica contenuto pagina                │   │
│  │                                                                  │   │
│  │ Usato da: Research Agent                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ FILE_READER_MCP                                                 │   │
│  │                                                                  │   │
│  │ Tools:                                                          │   │
│  │ • file_reader_read       → Legge PDF/DOCX/TXT                   │   │
│  │ • file_reader_read_pdf   → Legge PDF con selezione pagine       │   │
│  │ • file_reader_list       → Lista file in directory              │   │
│  │                                                                  │   │
│  │ Usato da: Analysis Agent (per documenti locali)                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ REPORT_WRITER_MCP                                               │   │
│  │                                                                  │   │
│  │ Tools:                                                          │   │
│  │ • report_writer_create   → Crea report MD/HTML/JSON             │   │
│  │ • report_writer_append   → Aggiunge sezione a report            │   │
│  │ • report_writer_export   → Esporta dati strutturati             │   │
│  │                                                                  │   │
│  │ Usato da: Synthesis Agent                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Parametri Configurabili

```python
# config.py

# LLM
OLLAMA_MODEL = "llama3.2:3b"     # Modello da usare
LLM_TEMPERATURE = 0.3            # Creatività (0=deterministico, 1=creativo)
LLM_MAX_TOKENS = 2048            # Max token in output

# RICERCA
MAX_SEARCH_RESULTS = 10          # Risultati web per query
WEB_TIMEOUT = 15                 # Timeout HTTP in secondi

# ANALISI (protezione context window)
MAX_WEB_RESULTS_FOR_ANALYSIS = 5      # Risultati passati ad Analysis
MAX_SNIPPET_LENGTH = 200              # Char per snippet
MAX_NEWS_FOR_ANALYSIS = 3             # News passate ad Analysis
MAX_DEEP_CONTENT_LENGTH = 1000        # Char per pagina fetchata
```

---

## Gestione Errori

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       GESTIONE ERRORI                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Ogni nodo può fallire. LangGraph gestisce così:                        │
│                                                                         │
│  research_node()                                                        │
│       │                                                                 │
│       ├── Successo ──► analysis_node()                                  │
│       │                                                                 │
│       └── Errore ────► END (con status: FAILED)                         │
│                                                                         │
│  Errori gestiti:                                                        │
│  • DuckDuckGo timeout        → Retry 1x, poi fallisce                   │
│  • LLM non risponde          → Errore salvato in state.errors           │
│  • JSON parse fallito        → Usa risposta raw come fallback           │
│  • File non trovato          → Salta con warning                        │
│                                                                         │
│  Output in caso di errore:                                              │
│  {                                                                      │
│    "status": "error",                                                   │
│    "errors": ["Errore LLM: model timeout..."],                          │
│    "partial_results": { ... }   ← Risultati parziali se disponibili     │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```