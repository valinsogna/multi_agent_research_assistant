"""
Quick Test - Test rapido del sistema.

Esegui con:
    python examples/quick_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_research_agent():
    """Test del solo Research Agent."""
    print("\n" + "="*50)
    print("TEST: Research Agent")
    print("="*50)
    
    from agents import create_research_agent
    
    agent = create_research_agent()
    
    # Test ricerca semplice
    results = await agent.research_topic(
        topic="Unicredit banca digitale",
        include_news=True,
        deep_search=False
    )
    
    print(f"\n✅ Ricerca completata!")
    print(f"   Web results: {len(results.get('web_results', []))}")
    print(f"   News results: {len(results.get('news_results', []))}")
    
    if results.get("web_results"):
        print("\n📄 Primi 3 risultati:")
        for i, r in enumerate(results["web_results"][:3], 1):
            print(f"   {i}. {r.get('title', 'N/A')[:60]}...")
    
    return results


async def test_analysis_agent():
    """Test dell'Analysis Agent."""
    print("\n" + "="*50)
    print("TEST: Analysis Agent")
    print("="*50)
    
    from agents import create_analysis_agent
    
    agent = create_analysis_agent()
    
    # Testo di esempio
    sample_text = """
    UniCredit è una delle principali banche europee, con sede a Milano.
    Nel 2024, la banca ha investito significativamente in AI e digital banking.
    Il CEO Andrea Orcel ha annunciato un piano strategico triennale.
    La capitalizzazione di mercato supera i 50 miliardi di euro.
    """
    
    entities = await agent.extract_entities(sample_text)
    
    print(f"\n✅ Estrazione entità completata!")
    print(f"   Risultato: {entities}")
    
    return entities


async def test_synthesis_agent():
    """Test del Synthesis Agent."""
    print("\n" + "="*50)
    print("TEST: Synthesis Agent")
    print("="*50)
    
    from agents import create_synthesis_agent
    
    agent = create_synthesis_agent()
    
    # Dati di esempio
    research_data = {
        "topic": "Test Report",
        "web_results": [
            {"title": "Source 1", "body": "Content about AI in banking"},
            {"title": "Source 2", "body": "Digital transformation trends"}
        ],
        "news_results": []
    }
    
    analysis_data = {
        "summary": "Test analysis summary",
        "temi_principali": ["AI", "Digital Banking", "Innovation"]
    }
    
    result = await agent.create_report(
        topic="Test Report - AI in Banking",
        research_data=research_data,
        analysis_data=analysis_data,
        output_format="markdown"
    )
    
    print(f"\n✅ Report generato!")
    print(f"   File: {result.get('file_path', 'N/A')}")
    print(f"   Parole: {result.get('word_count', 0)}")
    
    return result


async def test_full_workflow():
    """Test del workflow completo."""
    print("\n" + "="*50)
    print("TEST: Workflow Completo (A2A)")
    print("="*50)
    
    from orchestrator import run_research
    
    result = await run_research(
        query="AI generativa nel settore bancario",
        include_news=True,
        deep_search=False,
        output_format="markdown"
    )
    
    print(f"\n✅ Workflow completato!")
    print(f"   Status: {result.get('status', 'unknown')}")
    
    if result.get("report"):
        print(f"   Report: {result['report'].get('file_path', 'N/A')}")
    
    return result


async def main():
    """Menu principale test."""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║          QUICK TEST - Multi-Agent System          ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Verifica Ollama
    from config import validate_ollama_connection, OLLAMA_MODEL
    
    if not validate_ollama_connection():
        print("❌ Ollama non disponibile!")
        print("   Avvia con: ollama serve")
        return
    
    print(f"✅ Ollama connesso (modello: {OLLAMA_MODEL})")
    
    print("\nSeleziona test:")
    print("  1. Test Research Agent")
    print("  2. Test Analysis Agent")
    print("  3. Test Synthesis Agent")
    print("  4. Test Workflow Completo (A2A)")
    print("  5. Tutti i test")
    print("  0. Esci")
    
    choice = input("\nScelta: ")
    
    if choice == "1":
        await test_research_agent()
    elif choice == "2":
        await test_analysis_agent()
    elif choice == "3":
        await test_synthesis_agent()
    elif choice == "4":
        await test_full_workflow()
    elif choice == "5":
        await test_research_agent()
        await test_analysis_agent()
        await test_synthesis_agent()
        await test_full_workflow()
        print("\n" + "="*50)
        print("✅ TUTTI I TEST COMPLETATI!")
        print("="*50)
    else:
        print("Uscita.")


if __name__ == "__main__":
    asyncio.run(main())
