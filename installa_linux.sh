#!/bin/bash

# ==============================================
# INSTALLAZIONE GESTIONALE arTEper - Linux
# ==============================================

echo "=============================================="
echo "  INSTALLAZIONE GESTIONALE arTEper - Linux"
echo "=============================================="
echo ""

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funzione per verificare se un comando esiste
check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 1. Verifica Python
echo -n "🔍 Verifica Python... "
if check_command python3; then
    PY_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}✅ $PY_VERSION${NC}"
else
    echo -e "${RED}❌ NON TROVATO${NC}"
    echo "📥 Installazione Python in corso..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-tk
fi

# 2. Verifica pip
echo -n "🔍 Verifica pip... "
if check_command pip3; then
    PIP_VERSION=$(pip3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}✅ $PIP_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️ NON TROVATO${NC}"
    echo "📥 Installazione pip..."
    sudo apt install -y python3-pip
fi

# 3. Verifica tkinter
echo -n "🔍 Verifica tkinter... "
if python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️ NON TROVATO${NC}"
    echo "📥 Installazione python3-tk..."
    sudo apt install -y python3-tk
fi

# 4. Crea ambiente virtuale
echo ""
echo -n "📦 Creazione ambiente virtuale... "

# Rimuovi ambiente virtuale esistente se presente
if [ -d "venv" ]; then
    rm -rf venv
fi

python3 -m venv venv
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ ERRORE${NC}"
    exit 1
fi

# 5. Attiva ambiente virtuale
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo "   ✅ Ambiente virtuale attivato"
else
    echo -e "${RED}❌ ERRORE nell'attivazione${NC}"
    exit 1
fi

# 6. Aggiorna pip
echo -n "🔄 Aggiornamento pip... "
pip install --upgrade pip > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️ WARNING${NC}"
fi

# 7. Verifica che requirements.txt esista
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ File requirements.txt non trovato!${NC}"
    echo "📝 Impossibile procedere senza il file requirements.txt"
    exit 1
fi

# 8. Installa dipendenze da requirements.txt
echo ""
echo "📥 Installazione dipendenze da requirements.txt..."
echo ""

# Conta il numero di pacchetti (escludendo righe vuote e commenti)
TOTALE=$(grep -v '^#' requirements.txt | grep -v '^$' | wc -l)
COUNT=0
ERRORI=0

while IFS= read -r pacchetto || [ -n "$pacchetto" ]; do
    # Salta righe vuote e commenti
    if [ -z "$pacchetto" ] || [[ "$pacchetto" == \#* ]]; then
        continue
    fi

    COUNT=$((COUNT + 1))
    echo -n "   [$COUNT/$TOTALE] $pacchetto... "

    pip install "$pacchetto" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        ERRORI=$((ERRORI + 1))
    fi
done < requirements.txt

# 9. Crea script di avvio (già eseguibile)
echo ""
echo -n "🚀 Creazione script di avvio (avvia_gestionale.sh)... "

cat > avvia_gestionale.sh << 'EOF'
#!/bin/bash
# Script di avvio per Gestionale arTEper
# Creato automaticamente da installa_linux.sh

# Attiva ambiente virtuale e avvia il programma
source venv/bin/activate
python3 main.py
EOF

chmod +x avvia_gestionale.sh
echo -e "${GREEN}✅${NC}"

# 10. Riepilogo finale
echo ""
echo "=============================================="
echo -e "${GREEN}✅ INSTALLAZIONE COMPLETATA!${NC}"
echo "=============================================="
echo ""
echo "📊 Riepilogo:"
echo "   - Pacchetti installati: $COUNT"
if [ $ERRORI -gt 0 ]; then
    echo -e "   - ${RED}Errori: $ERRORI${NC}"
else
    echo -e "   - ${GREEN}Errori: 0${NC}"
fi
echo ""
echo "📌 Per avviare il programma:"
echo "   ./avvia_gestionale.sh"
echo ""
