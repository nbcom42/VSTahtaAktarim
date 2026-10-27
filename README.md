# 📲 VS Tahta Aktarım

Okul tahtalarına (Pardus/Windows) cep telefonundan kablosuz dosya aktarım sistemi.

## Mimari

```
Telefon (herhangi ağ)
        │
        ▼
Relay Sunucu (Render/Railway - ücretsiz bulut)
        │
        ▼ polling (3 sn)
Masaüstü İstemci (kablolu ağdaki tahta)
        │
        ▼
~/Desktop/Tahtaya_Aktarilanlar/
```

Tahta kablolu ağda, telefon Wi-Fi veya mobil veride olabilir — ikisi de internete çıkabildiği sürece çalışır.

---

## 1. Relay Sunucuyu Deploy Et (Render — Ücretsiz)

### Adımlar:
1. [render.com](https://render.com) üzerinde ücretsiz hesap aç
2. **New → Web Service** seç
3. Bu repoyu GitHub'a push et, Render'da bağla
4. Ayarlar otomatik `render.yaml` dosyasından okunur
5. Deploy tamamlanınca URL'yi kopyala: `https://vs-tahta-relay.onrender.com`

### Manuel deploy (render.yaml olmadan):
| Alan | Değer |
|------|-------|
| Root Directory | `relay` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2` |

> **Not:** Render ücretsiz planda 15 dk hareketsizlikte uyur. İlk istek ~30 sn sürebilir.
> Ücretli plan ($7/ay) veya Railway ($5 kredi/ay) ile bu sorun olmaz.

---

## 2. Masaüstü Uygulamasını Kur

### Gereksinimler
- Python 3.9+
- Windows veya Pardus/Linux

### Kurulum

```bash
# Proje klasörüne gir
cd VSTahtaAktarim

# Bağımlılıkları yükle
pip install -r requirements_desktop.txt

# Uygulamayı çalıştır (RELAY_URL'yi kendi adresinle değiştir)
python desktop/app.py https://vs-tahta-relay.onrender.com
```

### Veya ortam değişkeni ile:
```bash
set RELAY_URL=https://vs-tahta-relay.onrender.com   # Windows
export RELAY_URL=https://vs-tahta-relay.onrender.com # Linux/Pardus
python desktop/app.py
```

---

## 3. Kullanım

1. Masaüstü uygulamayı aç
2. İsteğe bağlı: PIN korumasını etkinleştir (4 hane gir)
3. **"Oturumu Başlat"** butonuna tıkla
4. Ekrandaki QR kodu telefon kamerasıyla okut
5. Açılan sayfadan dosyaları seç veya sürükle-bırak
6. **"Tahtaya Gönder"** butonuna bas
7. Dosyalar otomatik olarak `~/Desktop/Tahtaya_Aktarilanlar/` klasörüne kaydedilir

---

## Proje Yapısı

```
VSTahtaAktarim/
├── desktop/
│   └── app.py                  # Masaüstü Tkinter istemcisi
├── relay/
│   ├── server.py               # Bulut relay Flask sunucusu
│   ├── requirements.txt        # Sunucu bağımlılıkları
│   └── Procfile                # Railway için
├── requirements_desktop.txt    # Masaüstü bağımlılıkları
├── render.yaml                 # Render otomatik deploy
└── README.md
```

---

## Özellikler

- ✅ Çoklu dosya yükleme (resim, video, müzik, belge)
- ✅ Sürükle-bırak arayüzü
- ✅ Gerçek zamanlı ilerleme çubuğu
- ✅ 4 haneli PIN koruması (isteğe bağlı)
- ✅ Aynı isimli dosyaları otomatik numaralandırma
- ✅ Maks. 500 MB dosya boyutu
- ✅ 1 saat sonra sunucudan otomatik temizleme
- ✅ Pardus (Linux) ve Windows uyumlu

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| QR kod açılmıyor | Render servisinin uyanık olduğunu kontrol et (ilk istek ~30 sn) |
| Dosya gelmiyor | RELAY_URL'nin doğru ayarlandığını kontrol et |
| PIN çalışmıyor | Tam 4 haneli sayı girildiğinden emin ol |
| Pardus'ta Tkinter yok | `sudo apt install python3-tk` |
