"""
VS Tahta Aktarım - Relay Sunucu
Render/Railway üzerinde çalışır. Telefon → Bulut → Masaüstü köprüsü kurar.
"""

import os
import uuid
import time
import hashlib
from flask import Flask, request, jsonify, render_template_string, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

# Bellekte oturum ve dosya kuyruğu
sessions = {}    # session_id -> {pin_hash, created_at, files: [file_id, ...]}
file_store = {}  # file_id -> {filename, data, session_id, uploaded_at}

CLEANUP_INTERVAL = 3600  # 1 saat

# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def cleanup_old_data():
    now = time.time()
    expired = [sid for sid, s in sessions.items() if now - s['created_at'] > CLEANUP_INTERVAL]
    for sid in expired:
        for fid in [fid for fid, f in file_store.items() if f['session_id'] == sid]:
            del file_store[fid]
        del sessions[sid]

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

# ─── Masaüstü İstemci API ─────────────────────────────────────────────────────

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Masaüstü uygulama yeni oturum açar"""
    cleanup_old_data()
    data = request.get_json() or {}
    pin = data.get('pin', '')
    session_id = str(uuid.uuid4())[:8].upper()
    sessions[session_id] = {
        'pin_hash': hash_pin(pin) if pin else None,
        'created_at': time.time(),
        'files': []
    }
    return jsonify({'session_id': session_id, 'status': 'ok'})

@app.route('/api/session/<session_id>/poll', methods=['GET'])
def poll_files(session_id):
    """Masaüstü uygulama yeni dosyaları sorgular"""
    if session_id not in sessions:
        return jsonify({'error': 'Geçersiz oturum'}), 404
    session = sessions[session_id]
    pending = session['files'].copy()
    session['files'] = []
    files_data = []
    for file_id in pending:
        if file_id in file_store:
            f = file_store[file_id]
            files_data.append({'file_id': file_id, 'filename': f['filename'], 'size': len(f['data'])})
    return jsonify({'files': files_data})

@app.route('/api/file/<file_id>/download', methods=['GET'])
def download_file(file_id):
    """Masaüstü uygulama dosyayı indirir, sonra sunucudan silinir"""
    if file_id not in file_store:
        return jsonify({'error': 'Dosya bulunamadı'}), 404
    f = file_store.pop(file_id)
    return Response(
        f['data'],
        mimetype='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{f["filename"]}"'}
    )

@app.route('/api/session/<session_id>/close', methods=['POST'])
def close_session(session_id):
    """Masaüstü uygulama oturumu kapatır"""
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({'status': 'ok'})

# ─── Mobil Arayüz ─────────────────────────────────────────────────────────────

MOBILE_HTML = '''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tahtaya Gönder</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { background: linear-gradient(135deg, #1e3a5f 0%, #0f2027 100%); min-height: 100vh; }
  .drop-zone { border: 2px dashed #60a5fa; transition: all 0.3s; }
  .drop-zone.drag-over { border-color: #34d399; background: rgba(52,211,153,0.1); transform: scale(1.02); }
  .file-item { animation: slideIn 0.3s ease; }
  @keyframes slideIn { from { opacity:0; transform:translateY(-10px); } to { opacity:1; transform:translateY(0); } }
  .progress-bar { transition: width 0.3s ease; }
</style>
</head>
<body class="flex items-center justify-center p-4">
<div class="w-full max-w-md">

  <div class="text-center mb-6">
    <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-2xl mb-3 shadow-lg">
      <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
      </svg>
    </div>
    <h1 class="text-2xl font-bold text-white">Tahtaya Gönder</h1>
    <p class="text-blue-300 text-sm mt-1">Oturum: <span class="font-mono font-bold text-yellow-400">{{ session_id }}</span></p>
  </div>

  {% if pin_required %}
  <div id="pinSection" class="bg-white/10 backdrop-blur rounded-2xl p-5 mb-4">
    <p class="text-white text-sm mb-3 text-center">🔒 Bu oturum PIN korumalı</p>
    <div class="flex gap-2">
      <input id="pinInput" type="number" placeholder="4 haneli PIN"
        class="flex-1 bg-white/20 text-white placeholder-blue-300 rounded-xl px-4 py-3 text-center text-xl font-mono tracking-widest border border-white/20 focus:outline-none focus:border-blue-400"
        oninput="if(this.value.length>4)this.value=this.value.slice(0,4)">
      <button onclick="verifyPin()" class="bg-blue-500 hover:bg-blue-600 text-white px-5 rounded-xl font-semibold transition">Gir</button>
    </div>
    <p id="pinError" class="text-red-400 text-sm text-center mt-2 hidden">Yanlış PIN!</p>
  </div>
  {% endif %}

  <div id="uploadSection" class="{{ 'hidden' if pin_required else '' }}">
    <div id="dropZone" class="drop-zone bg-white/10 backdrop-blur rounded-2xl p-8 text-center cursor-pointer mb-4"
      onclick="document.getElementById('fileInput').click()"
      ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
      <div class="inline-flex items-center justify-center w-12 h-12 bg-blue-500/30 rounded-full mb-3">
        <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
      </div>
      <p class="text-white font-medium">Dosya seç veya buraya sürükle</p>
      <p class="text-blue-300 text-xs mt-1">Resim, video, müzik, belge — maks. 500MB</p>
      <input id="fileInput" type="file" multiple class="hidden" onchange="handleFileSelect(event)">
    </div>

    <div id="fileList" class="space-y-2 mb-4"></div>

    <button id="uploadBtn" onclick="uploadFiles()"
      class="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-bold py-4 rounded-2xl shadow-lg transition hidden">
      📤 Tahtaya Gönder
    </button>

    <div id="progressSection" class="hidden mt-4">
      <div class="flex justify-between text-sm text-blue-300 mb-2">
        <span id="progressLabel">Yükleniyor...</span>
        <span id="progressPercent">0%</span>
      </div>
      <div class="bg-white/20 rounded-full h-3 overflow-hidden">
        <div id="progressBar" class="progress-bar bg-gradient-to-r from-blue-400 to-green-400 h-full rounded-full" style="width:0%"></div>
      </div>
    </div>
  </div>

  <div id="successSection" class="hidden text-center py-8">
    <div class="inline-flex items-center justify-center w-20 h-20 bg-green-500 rounded-full mb-4 shadow-lg">
      <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
      </svg>
    </div>
    <h2 class="text-2xl font-bold text-white mb-2">Gönderildi! 🎉</h2>
    <p id="successMsg" class="text-green-300 mb-6"></p>
    <button onclick="resetForm()" class="bg-white/20 hover:bg-white/30 text-white px-6 py-3 rounded-xl transition">
      Yeni Dosya Gönder
    </button>
  </div>

</div>
<script>
const SESSION_ID = "{{ session_id }}";
let verifiedPin = "";
let selectedFiles = [];

async function verifyPin() {
  const pin = document.getElementById('pinInput').value;
  const res = await fetch(`/upload/${SESSION_ID}/verify-pin`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pin})
  });
  const data = await res.json();
  if (data.ok) {
    verifiedPin = pin;
    document.getElementById('pinSection').classList.add('hidden');
    document.getElementById('uploadSection').classList.remove('hidden');
  } else {
    const err = document.getElementById('pinError');
    err.classList.remove('hidden');
    setTimeout(() => err.classList.add('hidden'), 2000);
  }
}

function handleDragOver(e) { e.preventDefault(); document.getElementById('dropZone').classList.add('drag-over'); }
function handleDragLeave() { document.getElementById('dropZone').classList.remove('drag-over'); }
function handleDrop(e) { e.preventDefault(); handleDragLeave(); addFiles(Array.from(e.dataTransfer.files)); }
function handleFileSelect(e) { addFiles(Array.from(e.target.files)); }
function addFiles(files) { selectedFiles = [...selectedFiles, ...files]; renderFileList(); }
function removeFile(i) { selectedFiles.splice(i, 1); renderFileList(); }
function formatSize(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(1) + ' MB';
}
function getIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  if (['jpg','jpeg','png','gif','webp'].includes(ext)) return '🖼️';
  if (['mp4','avi','mov','mkv'].includes(ext)) return '🎬';
  if (['mp3','wav','ogg','flac'].includes(ext)) return '🎵';
  if (['pdf'].includes(ext)) return '📄';
  if (['doc','docx'].includes(ext)) return '📝';
  if (['xls','xlsx','ppt','pptx'].includes(ext)) return '📊';
  if (['zip','rar','7z'].includes(ext)) return '🗜️';
  return '📁';
}
function renderFileList() {
  document.getElementById('fileList').innerHTML = selectedFiles.map((f, i) => `
    <div class="file-item flex items-center gap-3 bg-white/10 backdrop-blur rounded-xl px-4 py-3">
      <span class="text-2xl">${getIcon(f.name)}</span>
      <div class="flex-1 min-w-0">
        <p class="text-white text-sm font-medium truncate">${f.name}</p>
        <p class="text-blue-300 text-xs">${formatSize(f.size)}</p>
      </div>
      <button onclick="removeFile(${i})" class="text-red-400 hover:text-red-300 text-xl leading-none">×</button>
    </div>`).join('');
  document.getElementById('uploadBtn').classList.toggle('hidden', selectedFiles.length === 0);
}

async function uploadFiles() {
  if (!selectedFiles.length) return;
  document.getElementById('uploadBtn').classList.add('hidden');
  document.getElementById('progressSection').classList.remove('hidden');

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('files', f));
  if (verifiedPin) formData.append('pin', verifiedPin);

  await new Promise(resolve => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/upload/${SESSION_ID}`);
    xhr.upload.onprogress = e => {
      if (e.lengthComputable) {
        const pct = Math.round(e.loaded / e.total * 100);
        document.getElementById('progressBar').style.width = pct + '%';
        document.getElementById('progressPercent').textContent = pct + '%';
        document.getElementById('progressLabel').textContent = pct < 100 ? 'Yükleniyor...' : 'İşleniyor...';
      }
    };
    xhr.onload = () => {
      const res = JSON.parse(xhr.responseText);
      document.getElementById('progressSection').classList.add('hidden');
      if (res.ok) {
        document.getElementById('uploadSection').classList.add('hidden');
        document.getElementById('successMsg').textContent = `${res.count} dosya tahtaya başarıyla gönderildi!`;
        document.getElementById('successSection').classList.remove('hidden');
      } else {
        alert('Hata: ' + (res.error || 'Bilinmeyen hata'));
        document.getElementById('uploadBtn').classList.remove('hidden');
      }
      resolve();
    };
    xhr.onerror = () => { alert('Bağlantı hatası!'); resolve(); };
    xhr.send(formData);
  });
}

function resetForm() {
  selectedFiles = [];
  document.getElementById('fileList').innerHTML = '';
  document.getElementById('successSection').classList.add('hidden');
  document.getElementById('uploadSection').classList.remove('hidden');
  document.getElementById('progressBar').style.width = '0%';
}
</script>
</body>
</html>'''

@app.route('/upload/<session_id>', methods=['GET'])
def mobile_ui(session_id):
    if session_id not in sessions:
        return render_template_string(
            '<html><body style="background:#0f2027;color:white;display:flex;align-items:center;'
            'justify-content:center;height:100vh;font-family:sans-serif;text-align:center;">'
            '<div><h2>⚠️ Oturum Bulunamadı</h2><p style="color:#60a5fa">QR kodu yeniden okutun</p></div>'
            '</body></html>'), 404
    pin_required = sessions[session_id]['pin_hash'] is not None
    return render_template_string(MOBILE_HTML, session_id=session_id, pin_required=pin_required)

@app.route('/upload/<session_id>/verify-pin', methods=['POST'])
def verify_pin(session_id):
    if session_id not in sessions:
        return jsonify({'ok': False}), 404
    data = request.get_json() or {}
    session = sessions[session_id]
    if session['pin_hash'] is None:
        return jsonify({'ok': True})
    return jsonify({'ok': hash_pin(str(data.get('pin', ''))) == session['pin_hash']})

@app.route('/upload/<session_id>', methods=['POST'])
def receive_upload(session_id):
    if session_id not in sessions:
        return jsonify({'ok': False, 'error': 'Geçersiz oturum'}), 404
    session = sessions[session_id]
    if session['pin_hash']:
        if hash_pin(str(request.form.get('pin', ''))) != session['pin_hash']:
            return jsonify({'ok': False, 'error': 'Yanlış PIN'}), 403
    files = request.files.getlist('files')
    if not files:
        return jsonify({'ok': False, 'error': 'Dosya seçilmedi'}), 400
    count = 0
    for file in files:
        if not file.filename:
            continue
        file_id = str(uuid.uuid4())
        file_store[file_id] = {
            'filename': secure_filename(file.filename),
            'data': file.read(),
            'session_id': session_id,
            'uploaded_at': time.time()
        }
        session['files'].append(file_id)
        count += 1
    return jsonify({'ok': True, 'count': count})

@app.route('/')
def index():
    return jsonify({'service': 'VS Tahta Aktarım Relay', 'status': 'running',
                    'sessions': len(sessions), 'queued_files': len(file_store)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
