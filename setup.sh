#!/bin/bash
# =============================================================================
# Setup Script - Multi-Agent Research Assistant
# =============================================================================

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     SETUP - Multi-Agent Research Assistant                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

# 1. Check Python
echo ""
echo "📌 Step 1: Verifica Python..."
python3 --version || { echo "❌ Python 3 richiesto"; exit 1; }

# 2. Create venv
echo ""
echo "📌 Step 2: Creazione ambiente virtuale..."
python3 -m venv venv 2>/dev/null || echo "   venv già esiste"
source venv/bin/activate

# 3. Install dependencies
echo ""
echo "📌 Step 3: Installazione dipendenze..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "   ✅ Dipendenze installate"

# 4. Create directories
echo ""
echo "📌 Step 4: Creazione directories..."
mkdir -p outputs data .cache
echo "   ✅ Done"

# 5. Check Ollama
echo ""
echo "📌 Step 5: Verifica Ollama..."
if command -v ollama &> /dev/null; then
    echo "   ✅ Ollama trovato"
    echo "   Scarico modello DeepSeek..."
    ollama pull deepseek-r1:7b || ollama pull llama3.2:3b || echo "   ⚠️ Scarica manualmente"
else
    echo "   ⚠️ Ollama non trovato"
    echo "   Installa: curl -fsSL https://ollama.com/install.sh | sh"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    ✅ SETUP COMPLETATO!                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Prossimi passi:"
echo "  1. source venv/bin/activate"
echo "  2. ollama serve  (in altro terminale)"
echo "  3. python examples/quick_test.py"
