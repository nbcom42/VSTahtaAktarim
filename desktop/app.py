"""
VS Tahta Aktarım - Masaüstü İstemci
Relay sunucuya bağlanır, QR kod gösterir, dosyaları masaüstüne indirir.
"""

import os
import sys
import time
import threading
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import qrcode
from PIL import Image, ImageTk

# ─── Ayarlar ──────────────────────────────────────────────────────────────────

# Render/Railway'e deploy ettikten sonra bu URL'yi güncelleyin
RELAY_URL = os.environ.get('RELAY_URL', 'https://vs-tahta-relay.onrender.com')
POLL_INTERVAL = 3  # saniye
SAVE_DIR = Path.home() / 'Desktop' / 'Tahtaya_Aktarilanlar'

# ─── Ana Uygulama ─────────────────────────────────────────────────────────────

class TahtaApp:
    def __init__(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        self.session_id = None
        self.polling = False
        self.poll_thread = None
        self.pin = tk.StringVar()
        self.pin_enabled = tk.BooleanVar(value=False)
        self._build_ui()

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title('VS Tahta Aktarım')
        self.root.geometry('480x680')
        self.root.resizable(False, False)
        self.root.configure(bg='#0f2027')
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

        # Başlık
        tk.Label(self.root, text='📲 VS Tahta Aktarım', font=('Segoe UI', 18, 'bold'),
                 bg='#0f2027', fg='white').pack(pady=(20, 4))
        tk.Label(self.root, text='Telefonunuzla QR kodu okutun', font=('Segoe UI', 10),
                 bg='#0f2027', fg='#60a5fa').pack()

        # PIN Ayarları
        pin_frame = tk.Frame(self.root, bg='#1e3a5f', bd=0)
        pin_frame.pack(fill='x', padx=20, pady=(16, 0))
        tk.Checkbutton(pin_frame, text='PIN Koruması', variable=self.pin_enabled,
                       bg='#1e3a5f', fg='white', selectcolor='#1e3a5f',
                       activebackground='#1e3a5f', activeforeground='white',
                       font=('Segoe UI', 10)).pack(side='left', padx=10, pady=8)
        self.pin_entry = tk.Entry(pin_frame, textvariable=self.pin, width=8,
                                  font=('Courier', 14), justify='center', show='●')
        self.pin_entry.pack(side='left', padx=(0, 10), pady=8)
        tk.Label(pin_frame, text='(4 hane)', font=('Segoe UI', 9),
                 bg='#1e3a5f', fg='#93c5fd').pack(side='left')

        # Başlat/Durdur Butonu
        self.btn = tk.Button(self.root, text='▶  Oturumu Başlat',
                             font=('Segoe UI', 12, 'bold'), bg='#3b82f6', fg='white',
                             activebackground='#2563eb', activeforeground='white',
                             relief='flat', cursor='hand2', padx=20, pady=10,
                             command=self._toggle_session)
        self.btn.pack(pady=16)

        # QR Kod Alanı
        self.qr_frame = tk.Frame(self.root, bg='white', width=260, height=260)
        self.qr_frame.pack(pady=4)
        self.qr_frame.pack_propagate(False)
        self.qr_label = tk.Label(self.qr_frame, bg='white',
                                  text='QR kod burada\ngösterilecek',
                                  font=('Segoe UI', 11), fg='#94a3b8')
        self.qr_label.pack(expand=True)

        # URL Etiketi
        self.url_label = tk.Label(self.root, text='', font=('Courier', 10),
                                   bg='#0f2027', fg='#fbbf24', wraplength=440)
        self.url_label.pack(pady=6)

        # Durum
        self.status_label = tk.Label(self.root, text='● Bekleniyor',
                                      font=('Segoe UI', 10), bg='#0f2027', fg='#94a3b8')
        self.status_label.pack()

        # Dosya Listesi
        list_frame = tk.Frame(self.root, bg='#1e3a5f')
        list_frame.pack(fill='both', expand=True, padx=20, pady=(12, 0))
        tk.Label(list_frame, text='Aktarılan Dosyalar', font=('Segoe UI', 10, 'bold'),
                 bg='#1e3a5f', fg='#93c5fd').pack(anchor='w', padx=10, pady=(8, 4))

        self.file_listbox = tk.Listbox(list_frame, bg='#0f2027', fg='#e2e8f0',
                                        font=('Segoe UI', 9), relief='flat',
                                        selectbackground='#3b82f6', height=8,
                                        borderwidth=0)
        self.file_listbox.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Klasörü Aç Butonu
        tk.Button(self.root, text='📂 Klasörü Aç', font=('Segoe UI', 10),
                  bg='#1e3a5f', fg='#93c5fd', relief='flat', cursor='hand2',
                  command=lambda: os.startfile(SAVE_DIR)).pack(pady=(8, 16))

    def _toggle_session(self):
        if self.polling:
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self):
        pin = self.pin.get().strip() if self.pin_enabled.get() else ''
        if self.pin_enabled.get() and (not pin.isdigit() or len(pin) != 4):
            messagebox.showwarning('PIN Hatası', '4 haneli sayısal PIN giriniz.')
            return

        self._set_status('Sunucuya bağlanılıyor...', '#fbbf24')
        try:
            res = requests.post(f'{RELAY_URL}/api/session/create',
                                json={'pin': pin}, timeout=10)
            data = res.json()
            if data.get('status') != 'ok':
                raise ValueError('Sunucu hatası')
            self.session_id = data['session_id']
        except Exception as e:
            self._set_status(f'Bağlantı hatası: {e}', '#f87171')
            messagebox.showerror('Hata', f'Relay sunucuya bağlanılamadı:\n{e}\n\nRELAY_URL ayarını kontrol edin.')
            return

        upload_url = f'{RELAY_URL}/upload/{self.session_id}'
        self._show_qr(upload_url)
        self.url_label.config(text=upload_url)
        self.polling = True
        self.btn.config(text='⏹  Oturumu Kapat', bg='#ef4444', activebackground='#dc2626')
        self._set_status(f'● Aktif — Oturum: {self.session_id}', '#34d399')

        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()

    def _stop_session(self):
        self.polling = False
        if self.session_id:
            try:
                requests.post(f'{RELAY_URL}/api/session/{self.session_id}/close', timeout=5)
            except Exception:
                pass
            self.session_id = None
        self.btn.config(text='▶  Oturumu Başlat', bg='#3b82f6', activebackground='#2563eb')
        self.qr_label.config(image='', text='QR kod burada\ngösterilecek')
        self.url_label.config(text='')
        self._set_status('● Bekleniyor', '#94a3b8')

    def _show_qr(self, url):
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0f2027', back_color='white').convert('RGB')
        img = img.resize((250, 250), Image.LANCZOS)
        self._qr_photo = ImageTk.PhotoImage(img)
        self.qr_label.config(image=self._qr_photo, text='')

    def _poll_loop(self):
        while self.polling and self.session_id:
            try:
                res = requests.get(f'{RELAY_URL}/api/session/{self.session_id}/poll', timeout=10)
                data = res.json()
                for file_info in data.get('files', []):
                    self._download_file(file_info)
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)

    def _download_file(self, file_info):
        try:
            res = requests.get(f'{RELAY_URL}/api/file/{file_info["file_id"]}/download',
                               timeout=60, stream=True)
            filename = file_info['filename']
            save_path = SAVE_DIR / filename
            # Aynı isimde dosya varsa numaralandır
            counter = 1
            while save_path.exists():
                stem, suffix = Path(filename).stem, Path(filename).suffix
                save_path = SAVE_DIR / f'{stem}_{counter}{suffix}'
                counter += 1

            with open(save_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_kb = save_path.stat().st_size // 1024
            display = f'✅ {save_path.name} ({size_kb} KB)'
            self.root.after(0, lambda d=display: self._add_to_list(d))
            self.root.after(0, lambda: self._set_status(f'● Aktif — Son: {save_path.name}', '#34d399'))
        except Exception as e:
            err = f'❌ {file_info["filename"]}: {e}'
            self.root.after(0, lambda d=err: self._add_to_list(d))

    def _add_to_list(self, text):
        self.file_listbox.insert(0, text)

    def _set_status(self, text, color):
        self.status_label.config(text=text, fg=color)

    def _on_close(self):
        self._stop_session()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

# ─── Giriş Noktası ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # RELAY_URL komut satırından da verilebilir: python app.py https://...
    if len(sys.argv) > 1:
        RELAY_URL = sys.argv[1].rstrip('/')
    TahtaApp().run()
