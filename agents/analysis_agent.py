"""
Analysis Agent - Agente specializzato nell'analisi di documenti e dati.

Responsabilità:
- Elaborazione documenti (PDF, DOCX, TXT)
- Estrazione entità e informazioni chiave
- Fact-checking incrociato
- Strutturazione dati non strutturati
"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from .base_agent import (
    BaseAgent,
    AgentMessage,
    MessageType,
    AgentCapability,
    get_registry
)


ANALYSIS_AGENT_PROMPT = """Sei un Analysis Agent specializzato nell'analisi di documenti e dati.

Il tuo ruolo è:
1. Estrarre informazioni strutturate da documenti
2. Identificare entità chiave (aziende, persone, date, numeri)
3. Verificare coerenza tra fonti diverse
4. Evidenziare inconsistenze o dati mancanti

Quando analizzi un documento:
- Identifica la struttura e le sezioni principali
- Estrai fatti, cifre e citazioni rilevanti
- Valuta la qualità e completezza delle informazioni
- Segnala potenziali bias o limitazioni

Rispondi in italiano. Sii preciso e metodico.
"""


class AnalysisAgent(BaseAgent):
    """Agente per analisi documenti e dati."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(
            agent_id="analysis_agent",
            name="Analysis Agent",
            description="Analisi documenti, estrazione dati, fact-checking",
            system_prompt=ANALYSIS_AGENT_PROMPT,
            model=model
        )
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="analyze_document",
                description="Analizza un documento estraendo informazioni chiave",
                input_schema={"document_path": "str", "focus_areas": "list"},
                output_schema={"entities": "list", "summary": "str", "structure": "dict"}
            ),
            AgentCapability(
                name="extract_entities",
                description="Estrae entità nominate da un testo",
                input_schema={"text": "str"},
                output_schema={"entities": "dict"}
            ),
            AgentCapability(
                name="fact_check",
                description="Verifica coerenza tra fonti multiple",
                input_schema={"claims": "list", "sources": "list"},
                output_schema={"verified": "list", "conflicts": "list"}
            ),
            AgentCapability(
                name="analyze_data",
                description="Analizza dati strutturati da ricerca web",
                input_schema={"data": "dict"},
                output_schema={"insights": "list", "summary": "str"}
            )
        ]
    
    async def process_request(self, request: AgentMessage) -> AgentMessage:
        """Processa richieste di analisi."""
        self.log(f"Ricevuta richiesta: {request.message_type.value}")
        
        content = request.content
        action = content.get("action", "analyze")
        
        try:
            if action == "analyze_document":
                result = await self.analyze_document(
                    document_path=content.get("document_path"),
                    focus_areas=content.get("focus_areas", [])
                )
            elif action == "extract_entities":
                result = await self.extract_entities(content.get("text", ""))
            elif action == "fact_check":
                result = await self.fact_check(
                    claims=content.get("claims", []),
                    sources=content.get("sources", [])
                )
            elif action == "analyze_research":
                result = await self.analyze_research_results(content.get("data", {}))
            else:
                return self.create_response(
                    original_request=request,
                    content={"error": f"Azione non supportata: {action}"},
                    success=False
                )
            
            return self.create_response(
                original_request=request,
                content={"result": result},
                success=True
            )
            
        except Exception as e:
            self.log(f"Errore: {e}", "ERROR")
            return self.create_response(
                original_request=request,
                content={"error": str(e)},
                success=False
            )
    
    async def analyze_document(
        self,
        document_path: Optional[str] = None,
        document_text: Optional[str] = None,
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analizza un documento estraendo informazioni strutturate.
        
        Args:
            document_path: Percorso al documento
            document_text: Testo già estratto (alternativo)
            focus_areas: Aree specifiche su cui concentrarsi
            
        Returns:
            Analisi strutturata
        """
        self.log("Avvio analisi documento...")
        
        # Ottieni testo
        if document_text:
            text = document_text
        elif document_path:
            text = await self._read_document(document_path)
        else:
            return {"error": "Nessun documento fornito"}
        
        if not text:
            return {"error": "Documento vuoto o non leggibile"}
        
        # Analisi con LLM
        focus_str = ", ".join(focus_areas) if focus_areas else "tutti gli aspetti rilevanti"
        
        prompt = f"""Analizza questo documento concentrandoti su: {focus_str}

Fornisci:
1. STRUTTURA: Identificazione delle sezioni principali
2. ENTITÀ: Persone, organizzazioni, date, luoghi, numeri chiave
3. FATTI PRINCIPALI: Lista dei fatti più importanti
4. TEMI: Temi e argomenti trattati
5. QUALITÀ: Valutazione completezza e affidabilità (0-10)
6. SINTESI: Riassunto in 3-5 frasi

Rispondi in formato JSON."""

        context = f"DOCUMENTO:\n{text[:8000]}"  # Limita lunghezza
        
        response = await self.invoke_llm(prompt, context)
        
        # Prova parsing JSON
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        analysis["document_length"] = len(text)
        analysis["analyzed_at"] = datetime.now().isoformat()
        
        return analysis
    
    async def _read_document(self, path: str) -> str:
        """Legge un documento (PDF, DOCX, TXT)."""
        file_path = Path(path)
        
        if not file_path.exists():
            self.log(f"File non trovato: {path}", "ERROR")
            return ""
        
        ext = file_path.suffix.lower()
        
        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                
            elif ext in [".docx", ".doc"]:
                from docx import Document
                doc = Document(str(file_path))
                text = "\n".join(p.text for p in doc.paragraphs)
                
            else:  # txt, md, etc.
                text = file_path.read_text(encoding="utf-8")
            
            return text
            
        except Exception as e:
            self.log(f"Errore lettura {path}: {e}", "ERROR")
            return ""
    
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Estrae entità nominate da un testo.
        
        Returns:
            Dict con categorie: persone, organizzazioni, luoghi, date, numeri
        """
        if not text:
            return {}
        
        prompt = """Estrai le seguenti entità dal testo:

1. PERSONE: Nomi di persone menzionate
2. ORGANIZZAZIONI: Aziende, istituzioni, enti
3. LUOGHI: Città, paesi, indirizzi
4. DATE: Date e periodi temporali
5. NUMERI: Cifre significative (importi, percentuali, quantità)
6. CONCETTI: Termini tecnici o concetti chiave

Rispondi in JSON con queste chiavi: persons, organizations, locations, dates, numbers, concepts"""

        response = await self.invoke_llm(prompt, text[:5000])
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "numbers": [],
            "concepts": [],
            "raw": response
        }
    
    async def fact_check(
        self,
        claims: List[str],
        sources: List[Dict]
    ) -> Dict[str, Any]:
        """
        Verifica coerenza tra affermazioni e fonti.
        
        Args:
            claims: Lista di affermazioni da verificare
            sources: Lista di fonti con testo
            
        Returns:
            Risultato verifica per ogni claim
        """
        if not claims:
            return {"error": "Nessuna affermazione da verificare"}
        
        # Prepara contesto fonti
        sources_text = []
        for i, s in enumerate(sources[:5], 1):
            title = s.get("title", f"Fonte {i}")
            content = s.get("content", s.get("snippet", ""))[:500]
            sources_text.append(f"[{i}] {title}: {content}")
        
        sources_context = "\n\n".join(sources_text)
        
        # Prepara claims
        claims_text = "\n".join(f"- {c}" for c in claims)
        
        prompt = f"""Verifica queste affermazioni rispetto alle fonti fornite:

AFFERMAZIONI:
{claims_text}

Per ogni affermazione indica:
- SUPPORTATA: La fonte conferma
- CONTRADDETTA: La fonte smentisce
- NON VERIFICABILE: Informazione non presente nelle fonti
- PARZIALE: Parzialmente supportata

Fornisci anche spiegazione e riferimento alla fonte.
Rispondi in JSON con array "verifications"."""

        response = await self.invoke_llm(prompt, sources_context)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {"raw_verification": response}
    
    async def analyze_research_results(self, data: Dict) -> Dict[str, Any]:
        """
        Analizza risultati di ricerca dal Research Agent.
        
        Args:
            data: Output dal ResearchAgent.research_topic()
            
        Returns:
            Analisi approfondita dei risultati
        """
        self.log("Analisi risultati ricerca...")
        
        # Estrai contenuti
        web_results = data.get("web_results", [])
        news_results = data.get("news_results", [])
        deep_content = data.get("deep_content", [])
        topic = data.get("topic", "Non specificato")
        
        # Prepara contesto
        context_parts = [f"Topic di ricerca: {topic}\n"]
        
        # Web results
        context_parts.append("## Risultati Web:")
        for r in web_results[:5]:
            title = r.get("title", "")
            snippet = r.get("body", r.get("snippet", ""))[:200]
            context_parts.append(f"- {title}: {snippet}")
        
        # News
        if news_results:
            context_parts.append("\n## News Recenti:")
            for r in news_results[:3]:
                title = r.get("title", "")
                source = r.get("source", "")
                context_parts.append(f"- [{source}] {title}")
        
        # Deep content
        if deep_content:
            context_parts.append("\n## Contenuti Approfonditi:")
            for d in deep_content[:2]:
                content = d.get("content", "")[:1000]
                context_parts.append(f"---\n{content}\n---")
        
        context = "\n".join(context_parts)
        
        prompt = """Analizza questi risultati di ricerca e fornisci:

1. TEMI PRINCIPALI: I 3-5 temi più ricorrenti
2. FONTI AFFIDABILI: Quali fonti sembrano più autorevoli
3. CONTRADDIZIONI: Eventuali informazioni contrastanti
4. TREND: Se emerge un trend o direzione comune
5. LACUNE: Informazioni che mancano o andrebbero approfondite
6. SINTESI: Riassunto strutturato (200-300 parole)

Rispondi in JSON."""

        response = await self.invoke_llm(prompt, context)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        # Aggiungi metadata
        analysis["sources_analyzed"] = {
            "web": len(web_results),
            "news": len(news_results),
            "deep": len(deep_content)
        }
        analysis["analyzed_at"] = datetime.now().isoformat()
        
        return analysis


# Factory function
def create_analysis_agent(model: Optional[str] = None) -> AnalysisAgent:
    """Crea e registra un Analysis Agent."""
    agent = AnalysisAgent(model=model)
    get_registry().register(agent)
    return agent
