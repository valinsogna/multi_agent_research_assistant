"""
Esempio: Financial Research Assistant

Caso d'uso rilevante per:
- Sistema multi-agente A2A
- MCP tools per web search
- Analisi dati finanziari
- Generazione report professionale

Esegui con:
    python examples/financial_research.py
"""

import asyncio
import sys
from pathlib import Path

# Aggiungi path progetto
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from orchestrator import ResearchOrchestrator, run_research
from config import validate_ollama_connection, OLLAMA_MODEL


console = Console()


def print_banner():
    """Stampa banner iniziale."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🏦  FINANCIAL RESEARCH ASSISTANT                            ║
    ║                                                               ║
    ║   Multi-Agent System con MCP                                  ║
    ║   Demo                                                        ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


def check_prerequisites():
    """Verifica prerequisiti."""
    console.print("\n[bold]Verifica prerequisiti...[/bold]")
    
    # Check Ollama
    if validate_ollama_connection():
        console.print(f"  ✅ Ollama connesso (modello: {OLLAMA_MODEL})")
        return True
    else:
        console.print("  ❌ Ollama non disponibile", style="red")
        console.print("\n[yellow]Per avviare Ollama:[/yellow]")
        console.print("  1. Apri un nuovo terminale")
        console.print("  2. Esegui: ollama serve")
        console.print("  3. Riesegui questo script")
        return False


async def demo_basic_research():
    """Demo: ricerca base su un topic finanziario."""
    
    console.print(Panel.fit(
        "[bold]DEMO 1: Ricerca Base[/bold]\n"
        "Topic: AI nel settore bancario italiano",
        border_style="cyan"
    ))
    
    result = await run_research(
        query="Intelligenza artificiale settore bancario Italia 2026",
        include_news=True,
        deep_search=False,
        output_format="markdown"
    )
    
    return result


async def demo_market_analysis():
    """Demo: analisi di mercato con deep search."""
    
    console.print(Panel.fit(
        "[bold]DEMO 2: Analisi di Mercato[/bold]\n"
        "Topic: Trend fintech e digital banking",
        border_style="green"
    ))
    
    result = await run_research(
        query="Fintech digital banking trends Europe 2026",
        include_news=True,
        deep_search=True,  # Più approfondito
        output_format="html"
    )
    
    return result


async def demo_regulatory_research():
    """Demo: ricerca su normative (rilevante per banche)."""
    
    console.print(Panel.fit(
        "[bold]DEMO 3: Ricerca Normativa[/bold]\n"
        "Topic: Regolamentazione AI nel settore finanziario",
        border_style="yellow"
    ))
    
    result = await run_research(
        query="EU AI Act financial services banking regulation",
        include_news=True,
        deep_search=False,
        output_format="markdown"
    )
    
    return result


def display_result(result: dict, demo_name: str):
    """Visualizza risultati in modo formattato."""
    
    status = result.get("status", "unknown")
    
    if status == "success":
        console.print(f"\n[bold green]✅ {demo_name} completato![/bold green]")
        
        # Info report
        if "report" in result:
            report = result["report"]
            console.print(f"  📄 Report: {report.get('file_path', 'N/A')}")
            console.print(f"  📊 Parole: {report.get('word_count', 0)}")
        
        # Insights
        if "insights" in result:
            insights = result["insights"]
            themes = insights.get("themes", [])
            if themes:
                console.print(f"  🎯 Temi principali:")
                for t in themes[:3]:
                    console.print(f"     • {t}")
        
        # Timing
        console.print(f"  ⏱️  Durata: {result.get('total_duration_seconds', 0):.1f}s")
        
    else:
        console.print(f"\n[bold red]❌ {demo_name} fallito[/bold red]")
        errors = result.get("errors", [])
        for e in errors:
            console.print(f"  Error: {e}", style="red")


async def interactive_mode():
    """Modalità interattiva: l'utente inserisce la query."""
    
    console.print(Panel.fit(
        "[bold]MODALITÀ INTERATTIVA[/bold]\n"
        "Inserisci il tuo argomento di ricerca",
        border_style="magenta"
    ))
    
    query = console.input("\n[bold cyan]📝 Argomento da ricercare:[/bold cyan] ")
    
    if not query.strip():
        console.print("[yellow]Nessun argomento inserito, uso default[/yellow]")
        query = "Generative AI applications in banking"
    
    # Opzioni
    console.print("\n[bold]Opzioni:[/bold]")
    include_news = console.input("  Includere news? [S/n]: ").lower() != 'n'
    deep_search = console.input("  Deep search (più lento)? [s/N]: ").lower() == 's'
    
    format_choice = console.input("  Formato output [markdown/html]: ").lower()
    output_format = "html" if format_choice == "html" else "markdown"
    
    console.print(f"\n[bold]Avvio ricerca su:[/bold] {query}")
    console.print(f"  News: {include_news} | Deep: {deep_search} | Format: {output_format}\n")
    
    result = await run_research(
        query=query,
        include_news=include_news,
        deep_search=deep_search,
        output_format=output_format
    )
    
    return result


async def main():
    """Main entry point."""
    
    print_banner()
    
    # Verifica prerequisiti
    if not check_prerequisites():
        return
    
    console.print("\n[bold]Seleziona modalità:[/bold]")
    console.print("  1. Demo: AI nel settore bancario")
    console.print("  2. Demo: Analisi mercato fintech")
    console.print("  3. Demo: Ricerca normativa EU AI Act")
    console.print("  4. Modalità interattiva")
    console.print("  5. Esegui tutte le demo")
    console.print("  0. Esci")
    
    choice = console.input("\n[bold cyan]Scelta:[/bold cyan] ")
    
    if choice == "0":
        console.print("[yellow]Arrivederci![/yellow]")
        return
    
    elif choice == "1":
        result = await demo_basic_research()
        display_result(result, "Demo AI Banking")
        
    elif choice == "2":
        result = await demo_market_analysis()
        display_result(result, "Demo Fintech Analysis")
        
    elif choice == "3":
        result = await demo_regulatory_research()
        display_result(result, "Demo Regulatory Research")
        
    elif choice == "4":
        result = await interactive_mode()
        display_result(result, "Ricerca Personalizzata")
        
    elif choice == "5":
        console.print("\n[bold]Esecuzione di tutte le demo...[/bold]\n")
        
        # Demo 1
        result1 = await demo_basic_research()
        display_result(result1, "Demo 1")
        
        # Demo 2
        result2 = await demo_market_analysis()
        display_result(result2, "Demo 2")
        
        # Demo 3
        result3 = await demo_regulatory_research()
        display_result(result3, "Demo 3")
        
        console.print("\n[bold green]Tutte le demo completate![/bold green]")
        console.print("I report sono stati salvati nella cartella 'outputs/'")
    
    else:
        console.print("[yellow]Scelta non valida[/yellow]")
    
    # Mostra dove trovare i report
    console.print("\n" + "="*50)
    console.print("[bold]📁 I report sono stati salvati in:[/bold]")
    console.print("   ./outputs/")
    console.print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
