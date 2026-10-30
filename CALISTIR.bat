@echo off
chcp 65001 >nul
title VS Tahta Aktarim

echo.
echo  ========================================
echo   VS Tahta Aktarim - Baslatiliyor...
echo  ========================================
echo.

:: Python kurulu mu kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo.
    echo Python'u su adresten indirin:
    echo https://www.python.org/downloads/
    echo.
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

echo [1/2] Bagimliliklar yukleniyor...
python -m pip install --upgrade pip --quiet --disable-pip-version-check >nul 2>&1
python -m pip install requests "qrcode[pil]" Pillow --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [UYARI] Bazi paketler yuklenemedi, yine de devam ediliyor...
)

echo [2/2] Uygulama baslatiliyor...
echo.
python "%~dp0desktop\app.py" https://vstahtaaktarim.onrender.com

if errorlevel 1 (
    echo.
    echo [HATA] Uygulama beklenmedik sekilde kapandi.
    pause
)
