"""
Synthesis Agent - Agente specializzato nella sintesi e generazione report.

Responsabilità:
- Combinare informazioni da fonti multiple
- Generare report strutturati
- Creare executive summary
- Gestire citazioni e riferimenti
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


SYNTHESIS_AGENT_PROMPT = """Sei un Synthesis Agent specializzato nella creazione di report e documenti.

Il tuo ruolo è:
1. Combinare informazioni da fonti multiple in modo coerente
2. Creare report professionali e ben strutturati
3. Generare executive summary efficaci
4. Gestire citazioni e riferimenti appropriatamente

Quando crei un report:
- Usa una struttura chiara con sezioni logiche
- Mantieni un tono professionale ma accessibile
- Evidenzia insights e conclusioni chiave
- Includi sempre le fonti utilizzate
- Adatta il livello di dettaglio al pubblico

Rispondi in italiano. Produci contenuti di alta qualità.
"""


class SynthesisAgent(BaseAgent):
    """Agente per sintesi e generazione report."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(
            agent_id="synthesis_agent",
            name="Synthesis Agent",
            description="Sintesi informazioni e generazione report professionali",
            system_prompt=SYNTHESIS_AGENT_PROMPT,
            model=model
        )
        
        self._output_dir = Path("./outputs")
        self._output_dir.mkdir(exist_ok=True)
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="create_report",
                description="Genera un report completo da dati di ricerca e analisi",
                input_schema={"research_data": "dict", "analysis_data": "dict", "format": "str"},
                output_schema={"report": "str", "file_path": "str"}
            ),
            AgentCapability(
                name="create_summary",
                description="Genera un executive summary",
                input_schema={"content": "str", "max_words": "int"},
                output_schema={"summary": "str"}
            ),
            AgentCapability(
                name="combine_sources",
                description="Combina informazioni da fonti multiple",
                input_schema={"sources": "list"},
                output_schema={"combined": "str", "conflicts": "list"}
            )
        ]
    
    async def process_request(self, request: AgentMessage) -> AgentMessage:
        """Processa richieste di sintesi."""
        self.log(f"Ricevuta richiesta: {request.message_type.value}")
        
        content = request.content
        action = content.get("action", "report")
        
        try:
            if action == "create_report":
                result = await self.create_report(
                    topic=content.get("topic", "Report"),
                    research_data=content.get("research_data", {}),
                    analysis_data=content.get("analysis_data", {}),
                    output_format=content.get("format", "markdown")
                )
            elif action == "create_summary":
                result = await self.create_summary(
                    content=content.get("content", ""),
                    max_words=content.get("max_words", 200)
                )
            elif action == "combine_sources":
                result = await self.combine_sources(content.get("sources", []))
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
    
    async def create_report(
        self,
        topic: str,
        research_data: Dict,
        analysis_data: Dict,
        output_format: str = "markdown",
        audience: str = "business"
    ) -> Dict[str, Any]:
        """
        Genera un report completo.
        
        Args:
            topic: Argomento del report
            research_data: Dati dal Research Agent
            analysis_data: Dati dall'Analysis Agent
            output_format: Formato output (markdown, html)
            audience: Pubblico target (business, technical, executive)
            
        Returns:
            Report generato con metadata
        """
        self.log(f"Creazione report: {topic}")
        
        # 1. Prepara contesto
        context = self._prepare_context(research_data, analysis_data)
        
        # 2. Genera sezioni con LLM
        sections = await self._generate_sections(topic, context, audience)
        
        # 3. Genera executive summary
        summary = await self._generate_executive_summary(topic, sections)
        
        # 4. Assembla report
        report = self._assemble_report(
            topic=topic,
            summary=summary,
            sections=sections,
            sources=self._extract_sources(research_data),
            format=output_format
        )
        
        # 5. Salva file
        file_path = self._save_report(topic, report, output_format)
        
        return {
            "topic": topic,
            "format": output_format,
            "sections_count": len(sections),
            "word_count": len(report.split()),
            "file_path": str(file_path),
            "report_preview": report[:2000] + "..." if len(report) > 2000 else report,
            "generated_at": datetime.now().isoformat()
        }
    
    def _prepare_context(self, research_data: Dict, analysis_data: Dict) -> str:
        """Prepara contesto combinando ricerca e analisi."""
        parts = []
        
        # Topic
        topic = research_data.get("topic", analysis_data.get("topic", ""))
        if topic:
            parts.append(f"ARGOMENTO: {topic}\n")
        
        # Risultati ricerca
        if research_data:
            parts.append("## DATI DALLA RICERCA:")
            
            # Web results
            for r in research_data.get("web_results", [])[:5]:
                title = r.get("title", "")
                snippet = r.get("body", r.get("snippet", ""))[:200]
                parts.append(f"- {title}: {snippet}")
            
            # News
            for r in research_data.get("news_results", [])[:3]:
                title = r.get("title", "")
                source = r.get("source", "")
                parts.append(f"- [NEWS {source}] {title}")
            
            # Analysis from research
            if "analysis" in research_data:
                analysis = research_data["analysis"]
                if isinstance(analysis, dict) and "summary" in analysis:
                    parts.append(f"\nRIASSUNTO RICERCA: {analysis['summary']}")
        
        # Dati analisi
        if analysis_data:
            parts.append("\n## DATI DALL'ANALISI:")
            
            if "raw_analysis" in analysis_data:
                parts.append(analysis_data["raw_analysis"][:1500])
            else:
                # Temi principali
                if "temi_principali" in analysis_data:
                    parts.append(f"Temi: {analysis_data['temi_principali']}")
                
                # Sintesi
                if "sintesi" in analysis_data:
                    parts.append(f"Sintesi: {analysis_data['sintesi']}")
                    
                # Altri campi
                for key in ["trend", "lacune", "contraddizioni"]:
                    if key in analysis_data:
                        parts.append(f"{key.title()}: {analysis_data[key]}")
        
        return "\n".join(parts)
    
    async def _generate_sections(
        self, 
        topic: str, 
        context: str,
        audience: str
    ) -> List[Dict[str, str]]:
        """Genera le sezioni del report."""
        
        audience_instructions = {
            "business": "Usa linguaggio business-friendly, enfatizza impatti e opportunità",
            "technical": "Includi dettagli tecnici, usa terminologia appropriata",
            "executive": "Sii conciso, focus su decisioni e raccomandazioni"
        }
        
        prompt = f"""Crea le sezioni per un report su "{topic}".

Pubblico: {audience}
Istruzioni specifiche: {audience_instructions.get(audience, '')}

Genera 4-5 sezioni con questa struttura JSON:
[
  {{"title": "Titolo Sezione", "content": "Contenuto dettagliato della sezione (200-400 parole)"}},
  ...
]

Sezioni suggerite:
1. Contesto e Background
2. Analisi della Situazione Attuale
3. Trend e Sviluppi Chiave
4. Implicazioni e Opportunità
5. Conclusioni e Raccomandazioni

Basa il contenuto sui dati forniti. Sii specifico e cita fonti dove possibile."""

        response = await self.invoke_llm(prompt, context)
        
        # Parse JSON
        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                sections = json.loads(json_match.group())
                return sections
        except json.JSONDecodeError:
            pass
        
        # Fallback: crea sezione singola
        return [{"title": "Analisi", "content": response}]
    
    async def _generate_executive_summary(
        self,
        topic: str,
        sections: List[Dict]
    ) -> str:
        """Genera executive summary."""
        
        sections_text = "\n\n".join(
            f"## {s['title']}\n{s['content'][:500]}" 
            for s in sections
        )
        
        prompt = """Genera un Executive Summary (150-200 parole) che:
1. Catturi i punti chiave del report
2. Evidenzi le conclusioni principali
3. Indichi eventuali raccomandazioni
4. Sia standalone e leggibile indipendentemente

Scrivi in modo professionale e diretto."""

        summary = await self.invoke_llm(prompt, sections_text)
        return summary
    
    def _extract_sources(self, research_data: Dict) -> List[Dict]:
        """Estrae lista fonti dai dati di ricerca."""
        sources = []
        
        for r in research_data.get("web_results", []):
            sources.append({
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "type": "web"
            })
        
        for r in research_data.get("news_results", []):
            sources.append({
                "title": r.get("title", ""),
                "url": r.get("url", r.get("link", "")),
                "source": r.get("source", ""),
                "type": "news"
            })
        
        return sources[:10]  # Max 10 fonti
    
    def _assemble_report(
        self,
        topic: str,
        summary: str,
        sections: List[Dict],
        sources: List[Dict],
        format: str
    ) -> str:
        """Assembla il report finale."""
        
        if format == "html":
            return self._format_as_html(topic, summary, sections, sources)
        else:
            return self._format_as_markdown(topic, summary, sections, sources)
    
    def _format_as_markdown(
        self,
        topic: str,
        summary: str,
        sections: List[Dict],
        sources: List[Dict]
    ) -> str:
        """Formatta report in Markdown."""
        
        lines = [
            f"# {topic}",
            "",
            f"*Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}*",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            summary,
            "",
            "---",
            "",
            "## Indice",
            ""
        ]
        
        # TOC
        for i, s in enumerate(sections, 1):
            lines.append(f"{i}. [{s['title']}](#{s['title'].lower().replace(' ', '-')})")
        
        lines.extend(["", "---", ""])
        
        # Sezioni
        for s in sections:
            lines.extend([
                f"## {s['title']}",
                "",
                s['content'],
                "",
                ""
            ])
        
        # Fonti
        if sources:
            lines.extend([
                "---",
                "",
                "## Fonti e Riferimenti",
                ""
            ])
            
            for i, src in enumerate(sources, 1):
                title = src.get("title", "Fonte")
                url = src.get("url", "")
                src_type = src.get("type", "web")
                
                if url:
                    lines.append(f"{i}. [{title}]({url}) *[{src_type}]*")
                else:
                    lines.append(f"{i}. {title} *[{src_type}]*")
        
        # Footer
        lines.extend([
            "",
            "---",
            "",
            "*Report generato automaticamente da Multi-Agent Research Assistant*"
        ])
        
        return "\n".join(lines)
    
    def _format_as_html(
        self,
        topic: str,
        summary: str,
        sections: List[Dict],
        sources: List[Dict]
    ) -> str:
        """Formatta report in HTML."""
        
        sections_html = ""
        for s in sections:
            content_html = s['content'].replace('\n', '</p><p>')
            sections_html += f"""
            <section>
                <h2>{s['title']}</h2>
                <p>{content_html}</p>
            </section>
            """
        
        sources_html = ""
        for i, src in enumerate(sources, 1):
            title = src.get("title", "Fonte")
            url = src.get("url", "")
            if url:
                sources_html += f'<li><a href="{url}" target="_blank">{title}</a></li>'
            else:
                sources_html += f'<li>{title}</li>'
        
        return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>{topic}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; line-height: 1.6; color: #333; }}
        h1 {{ color: #1a365d; border-bottom: 3px solid #3182ce; padding-bottom: 15px; }}
        h2 {{ color: #2c5282; margin-top: 40px; }}
        .meta {{ color: #718096; font-style: italic; margin-bottom: 30px; }}
        .summary {{ background: #f7fafc; border-left: 4px solid #3182ce; padding: 20px; margin: 30px 0; }}
        section {{ margin: 30px 0; }}
        .sources {{ background: #edf2f7; padding: 20px; border-radius: 8px; margin-top: 40px; }}
        .sources h2 {{ margin-top: 0; }}
        .sources ul {{ padding-left: 20px; }}
        .sources a {{ color: #3182ce; }}
        footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #a0aec0; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{topic}</h1>
    <p class="meta">Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>{summary}</p>
    </div>
    
    {sections_html}
    
    <div class="sources">
        <h2>Fonti e Riferimenti</h2>
        <ol>{sources_html}</ol>
    </div>
    
    <footer>
        Report generato automaticamente da Multi-Agent Research Assistant
    </footer>
</body>
</html>"""
    
    def _save_report(self, topic: str, content: str, format: str) -> Path:
        """Salva report su file."""
        
        # Genera nome file
        clean_topic = "".join(c if c.isalnum() or c in " -_" else "" for c in topic)
        clean_topic = clean_topic.strip().replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        ext = "html" if format == "html" else "md"
        filename = f"report_{clean_topic}_{timestamp}.{ext}"
        
        file_path = self._output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        
        self.log(f"Report salvato: {file_path}")
        return file_path
    
    async def create_summary(self, content: str, max_words: int = 200) -> Dict[str, Any]:
        """
        Genera un summary di contenuto esistente.
        
        Args:
            content: Testo da riassumere
            max_words: Lunghezza massima in parole
            
        Returns:
            Summary con metadata
        """
        prompt = f"""Riassumi questo contenuto in massimo {max_words} parole.

Requisiti:
- Cattura i punti essenziali
- Mantieni la struttura logica
- Usa un tono professionale
- Sii conciso ma completo"""

        summary = await self.invoke_llm(prompt, content[:8000])
        
        return {
            "summary": summary,
            "original_length": len(content.split()),
            "summary_length": len(summary.split()),
            "compression_ratio": round(len(summary.split()) / max(1, len(content.split())), 2)
        }
    
    async def combine_sources(self, sources: List[Dict]) -> Dict[str, Any]:
        """
        Combina informazioni da fonti multiple.
        
        Args:
            sources: Lista di fonti con titolo e contenuto
            
        Returns:
            Testo combinato con eventuali conflitti
        """
        if not sources:
            return {"error": "Nessuna fonte fornita"}
        
        # Prepara contesto
        context_parts = []
        for i, s in enumerate(sources, 1):
            title = s.get("title", f"Fonte {i}")
            content = s.get("content", "")[:1500]
            context_parts.append(f"[FONTE {i}: {title}]\n{content}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = """Combina le informazioni dalle fonti fornite.

Compiti:
1. Identifica i temi comuni
2. Nota eventuali informazioni contrastanti
3. Crea una sintesi coerente che integri tutte le fonti
4. Indica quali informazioni provengono da quale fonte

Output in JSON:
{
    "combined_text": "testo integrato",
    "common_themes": ["tema1", "tema2"],
    "conflicts": [{"topic": "...", "source1_view": "...", "source2_view": "..."}],
    "unique_insights": [{"source": 1, "insight": "..."}]
}"""

        response = await self.invoke_llm(prompt, context)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {"combined_text": response}


# Factory function
def create_synthesis_agent(model: Optional[str] = None) -> SynthesisAgent:
    """Crea e registra un Synthesis Agent."""
    agent = SynthesisAgent(model=model)
    get_registry().register(agent)
    return agent
