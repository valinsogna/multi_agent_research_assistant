"""
MCP Server per generazione e salvataggio report.

Supporta:
- Report Markdown
- Report HTML
- Export JSON strutturato

Segue le best practices MCP di Anthropic.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from enum import Enum

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Server Initialization
# =============================================================================

mcp = FastMCP("report_writer_mcp")

# Directory di default per output
DEFAULT_OUTPUT_DIR = Path("./outputs")


# =============================================================================
# Pydantic Models
# =============================================================================

class ReportFormat(str, Enum):
    """Formato del report."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class ReportSection(BaseModel):
    """Sezione di un report."""
    title: str = Field(..., description="Titolo della sezione")
    content: str = Field(..., description="Contenuto della sezione")
    level: int = Field(default=2, description="Livello heading (1-4)", ge=1, le=4)


class CreateReportInput(BaseModel):
    """Input per creare un report."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    title: str = Field(
        ...,
        description="Titolo del report",
        min_length=1,
        max_length=200
    )
    sections: List[ReportSection] = Field(
        ...,
        description="Lista di sezioni del report",
        min_length=1
    )
    author: Optional[str] = Field(
        default="Research Assistant",
        description="Autore del report"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Sommario esecutivo opzionale"
    )
    format: ReportFormat = Field(
        default=ReportFormat.MARKDOWN,
        description="Formato output: markdown, html, json"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Percorso file output (opzionale, genera nome automatico se None)"
    )


class AppendToReportInput(BaseModel):
    """Input per aggiungere contenuto a un report esistente."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    file_path: str = Field(
        ...,
        description="Percorso del report esistente"
    )
    section: ReportSection = Field(
        ...,
        description="Nuova sezione da aggiungere"
    )


class ExportDataInput(BaseModel):
    """Input per export dati strutturati."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    data: dict = Field(
        ...,
        description="Dati da esportare (dizionario)"
    )
    filename: str = Field(
        ...,
        description="Nome file (senza estensione)"
    )
    include_metadata: bool = Field(
        default=True,
        description="Se True, include timestamp e versione"
    )


class FormatTextInput(BaseModel):
    """Input per formattare testo."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    text: str = Field(
        ...,
        description="Testo da formattare"
    )
    as_list: bool = Field(
        default=False,
        description="Se True, formatta come lista puntata"
    )
    as_table: bool = Field(
        default=False,
        description="Se True, cerca di formattare come tabella"
    )
    add_citations: bool = Field(
        default=False,
        description="Se True, aggiunge placeholder per citazioni"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def ensure_output_dir():
    """Assicura che la directory di output esista."""
    DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
    return DEFAULT_OUTPUT_DIR


def generate_filename(title: str, format: ReportFormat) -> str:
    """Genera un nome file dal titolo."""
    # Pulisci titolo
    clean_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
    clean_title = clean_title.strip().replace(" ", "_")[:50]
    
    # Aggiungi timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Estensione
    ext_map = {
        ReportFormat.MARKDOWN: "md",
        ReportFormat.HTML: "html",
        ReportFormat.JSON: "json"
    }
    
    return f"{clean_title}_{timestamp}.{ext_map[format]}"


def sections_to_markdown(title: str, sections: List[ReportSection], 
                         author: str, summary: Optional[str]) -> str:
    """Converte sezioni in Markdown."""
    lines = [
        f"# {title}",
        "",
        f"*Autore: {author}*  ",
        f"*Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}*",
        "",
        "---",
        ""
    ]
    
    if summary:
        lines.extend([
            "## Executive Summary",
            "",
            summary,
            "",
            "---",
            ""
        ])
    
    # Indice
    lines.extend([
        "## Indice",
        ""
    ])
    for i, section in enumerate(sections, 1):
        anchor = section.title.lower().replace(" ", "-")
        lines.append(f"{i}. [{section.title}](#{anchor})")
    lines.extend(["", "---", ""])
    
    # Sezioni
    for section in sections:
        heading = "#" * section.level
        lines.extend([
            f"{heading} {section.title}",
            "",
            section.content,
            "",
            ""
        ])
    
    # Footer
    lines.extend([
        "---",
        "",
        f"*Report generato automaticamente - {datetime.now().isoformat()}*"
    ])
    
    return "\n".join(lines)


def sections_to_html(title: str, sections: List[ReportSection],
                    author: str, summary: Optional[str]) -> str:
    """Converte sezioni in HTML."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='it'>",
        "<head>",
        f"  <title>{title}</title>",
        "  <meta charset='UTF-8'>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
        "    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }",
        "    h2 { color: #34495e; margin-top: 30px; }",
        "    .meta { color: #7f8c8d; font-style: italic; }",
        "    .summary { background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }",
        "    .toc { background: #ecf0f1; padding: 15px; margin: 20px 0; }",
        "    .toc a { color: #2980b9; text-decoration: none; }",
        "    .toc a:hover { text-decoration: underline; }",
        "    hr { border: none; border-top: 1px solid #bdc3c7; margin: 30px 0; }",
        "    footer { color: #95a5a6; font-size: 0.9em; margin-top: 40px; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>{title}</h1>",
        f"  <p class='meta'>Autore: {author} | Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
        "  <hr>"
    ]
    
    if summary:
        html_parts.extend([
            "  <div class='summary'>",
            "    <h2>Executive Summary</h2>",
            f"    <p>{summary}</p>",
            "  </div>"
        ])
    
    # TOC
    html_parts.extend([
        "  <div class='toc'>",
        "    <h2>Indice</h2>",
        "    <ol>"
    ])
    for section in sections:
        anchor = section.title.lower().replace(" ", "-")
        html_parts.append(f"      <li><a href='#{anchor}'>{section.title}</a></li>")
    html_parts.extend([
        "    </ol>",
        "  </div>",
        "  <hr>"
    ])
    
    # Sections
    for section in sections:
        anchor = section.title.lower().replace(" ", "-")
        tag = f"h{section.level}"
        html_parts.extend([
            f"  <{tag} id='{anchor}'>{section.title}</{tag}>",
            f"  <p>{section.content.replace(chr(10), '</p><p>')}</p>",
            ""
        ])
    
    # Footer
    html_parts.extend([
        "  <hr>",
        f"  <footer>Report generato automaticamente - {datetime.now().isoformat()}</footer>",
        "</body>",
        "</html>"
    ])
    
    return "\n".join(html_parts)


def sections_to_json(title: str, sections: List[ReportSection],
                    author: str, summary: Optional[str]) -> str:
    """Converte sezioni in JSON strutturato."""
    data = {
        "report": {
            "title": title,
            "author": author,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "sections": [
                {
                    "title": s.title,
                    "level": s.level,
                    "content": s.content,
                    "word_count": len(s.content.split())
                }
                for s in sections
            ],
            "total_sections": len(sections),
            "total_words": sum(len(s.content.split()) for s in sections)
        }
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool(
    name="report_writer_create",
    annotations={
        "title": "Create Report",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def report_writer_create(params: CreateReportInput) -> str:
    """
    Crea un nuovo report strutturato.
    
    Supporta Markdown, HTML e JSON. Include automaticamente
    indice, metadati e formattazione professionale.
    
    Args:
        params: CreateReportInput con title, sections, author, summary, format
    
    Returns:
        Conferma con percorso del file creato
    """
    try:
        output_dir = ensure_output_dir()
        
        # Genera contenuto in base al formato
        if params.format == ReportFormat.MARKDOWN:
            content = sections_to_markdown(
                params.title, params.sections, params.author, params.summary
            )
        elif params.format == ReportFormat.HTML:
            content = sections_to_html(
                params.title, params.sections, params.author, params.summary
            )
        else:  # JSON
            content = sections_to_json(
                params.title, params.sections, params.author, params.summary
            )
        
        # Determina percorso output
        if params.output_path:
            output_path = Path(params.output_path)
        else:
            filename = generate_filename(params.title, params.format)
            output_path = output_dir / filename
        
        # Scrivi file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
        return (
            f"## ✅ Report Creato\n\n"
            f"**Titolo:** {params.title}\n"
            f"**Formato:** {params.format.value}\n"
            f"**Sezioni:** {len(params.sections)}\n"
            f"**Percorso:** `{output_path}`\n"
            f"**Dimensione:** {len(content)} caratteri"
        )
        
    except Exception as e:
        return f"## ❌ Errore\n\nImpossibile creare il report: {str(e)}"


@mcp.tool(
    name="report_writer_append",
    annotations={
        "title": "Append to Report",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def report_writer_append(params: AppendToReportInput) -> str:
    """
    Aggiunge una sezione a un report Markdown esistente.
    
    Args:
        params: AppendToReportInput con file_path e section
    
    Returns:
        Conferma dell'aggiunta
    """
    path = Path(params.file_path)
    
    if not path.exists():
        return f"## ❌ Errore\n\nFile non trovato: {params.file_path}"
    
    try:
        # Leggi contenuto esistente
        existing = path.read_text(encoding="utf-8")
        
        # Prepara nuova sezione
        heading = "#" * params.section.level
        new_section = f"\n\n{heading} {params.section.title}\n\n{params.section.content}"
        
        # Trova posizione prima del footer (se presente)
        footer_marker = "---\n\n*Report generato"
        if footer_marker in existing:
            parts = existing.rsplit(footer_marker, 1)
            updated = parts[0] + new_section + "\n\n" + footer_marker + parts[1]
        else:
            updated = existing + new_section
        
        # Scrivi
        path.write_text(updated, encoding="utf-8")
        
        return (
            f"## ✅ Sezione Aggiunta\n\n"
            f"**Titolo:** {params.section.title}\n"
            f"**File:** `{path}`"
        )
        
    except Exception as e:
        return f"## ❌ Errore\n\n{str(e)}"


@mcp.tool(
    name="report_writer_export_data",
    annotations={
        "title": "Export Data",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def report_writer_export_data(params: ExportDataInput) -> str:
    """
    Esporta dati strutturati in formato JSON.
    
    Utile per salvare risultati intermedi, dati estratti,
    o qualsiasi struttura dati.
    
    Args:
        params: ExportDataInput con data, filename, include_metadata
    
    Returns:
        Conferma con percorso del file
    """
    try:
        output_dir = ensure_output_dir()
        
        export_data = params.data.copy()
        
        if params.include_metadata:
            export_data["_metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "source": "research_assistant",
                "version": "1.0"
            }
        
        filename = f"{params.filename}.json"
        output_path = output_dir / filename
        
        output_path.write_text(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        return (
            f"## ✅ Dati Esportati\n\n"
            f"**File:** `{output_path}`\n"
            f"**Chiavi:** {list(params.data.keys())}"
        )
        
    except Exception as e:
        return f"## ❌ Errore\n\n{str(e)}"


@mcp.tool(
    name="report_writer_format_text",
    annotations={
        "title": "Format Text",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def report_writer_format_text(params: FormatTextInput) -> str:
    """
    Formatta testo per inclusione in report.
    
    Può convertire in lista, tabella, o aggiungere
    placeholder per citazioni.
    
    Args:
        params: FormatTextInput con text, as_list, as_table, add_citations
    
    Returns:
        Testo formattato
    """
    text = params.text.strip()
    
    if params.as_list:
        # Divide per frasi/righe e crea lista
        import re
        items = re.split(r'[.;\n]', text)
        items = [item.strip() for item in items if item.strip()]
        formatted = "\n".join(f"- {item}" for item in items)
        
    elif params.as_table:
        # Cerca di creare tabella da dati strutturati
        lines = text.strip().split("\n")
        if len(lines) > 1:
            # Prima riga come header
            header = lines[0].split(",") if "," in lines[0] else lines[0].split("\t")
            header = [h.strip() for h in header]
            
            formatted = "| " + " | ".join(header) + " |\n"
            formatted += "| " + " | ".join(["---"] * len(header)) + " |\n"
            
            for line in lines[1:]:
                cells = line.split(",") if "," in line else line.split("\t")
                cells = [c.strip() for c in cells]
                # Padding se necessario
                while len(cells) < len(header):
                    cells.append("")
                formatted += "| " + " | ".join(cells[:len(header)]) + " |\n"
        else:
            formatted = text
    
    else:
        formatted = text
    
    if params.add_citations:
        # Aggiungi placeholder per citazioni
        formatted += "\n\n---\n**Fonti:** [Inserire riferimenti qui]"
    
    return formatted


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
