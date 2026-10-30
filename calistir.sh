#!/bin/bash

echo ""
echo " ========================================"
echo "  VS Tahta Aktarim - Baslatiliyor..."
echo " ========================================"
echo ""

# Python3 kurulu mu?
if ! command -v python3 &>/dev/null; then
    echo "[HATA] Python3 bulunamadi. Kuruluyor..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip
fi

# Tkinter kurulu mu?
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[1/3] Tkinter kuruluyor..."
    sudo apt-get install -y python3-tk -qq
fi

# pip kurulu mu?
python3 -m pip --version &>/dev/null
if [ $? -ne 0 ]; then
    echo "[2/3] pip kuruluyor..."
    sudo apt-get install -y python3-pip -qq
fi

echo "[3/3] Bagimliliklar yukleniyor..."
python3 -m pip install requests "qrcode[pil]" Pillow --quiet --disable-pip-version-check 2>/dev/null
# Sistem Python'unda hata verirse --break-system-packages ile dene
if [ $? -ne 0 ]; then
    python3 -m pip install requests "qrcode[pil]" Pillow --quiet \
        --disable-pip-version-check --break-system-packages 2>/dev/null
fi

echo "Uygulama baslatiliyor..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/desktop/app.py" https://vstahtaaktarim.onrender.com

if [ $? -ne 0 ]; then
    echo ""
    echo "[HATA] Uygulama beklenmedik sekilde kapandi."
    read -p "Devam etmek icin Enter'a basin..."
fi
