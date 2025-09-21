# full script with M2M100 integration
import whisper
import sounddevice as sd
import numpy as np
import queue
import sys
import asyncio
import socketio
from fastapi import FastAPI
import uvicorn
import json
import os
import subprocess
import time
import webbrowser
import platform
import signal
import psutil
from pathlib import Path

# ----------------------
# CONFIG
# ----------------------
CONFIG_FILE = "config.json"
FRONT_URL = "http://localhost:3000"
FRONT_DIR = "live-translation-front"

# Configuration par défaut
DEFAULT_CONFIG = {
    "model_name": "small",
    "sample_rate": 16000,
    "chunk_duration": 2,
    "volume_threshold": 0.01,
    "selected_microphone_id": None,
    "use_gpu": False,
    "force_mps": False,
    "spoken_language": "en",
    "target_language": "fr"
}

def kill_process_tree(proc):
    """Tue un process et tous ses enfants"""
    try:
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except Exception as e:
        print(f"❌ Erreur en tuant le process: {e}")

def load_config():
    """Charge la configuration depuis le fichier JSON et merge avec DEFAULT_CONFIG"""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
                print(f"✅ Configuration chargée depuis {CONFIG_FILE}")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de la config: {e}")
    else:
        print(f"📝 Création de la configuration par défaut")
    return config

def save_config(config):
    """Sauvegarde la configuration dans le fichier JSON"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"💾 Configuration sauvegardée dans {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")

# Charger la configuration
config = load_config()
MODEL_NAME = config.get("model_name")
SAMPLE_RATE = config.get("sample_rate")
CHUNK_DURATION = config.get("chunk_duration")
VOLUME_THRESHOLD = config.get("volume_threshold")
SELECTED_MICROPHONE_ID = config.get("selected_microphone_id")
USE_GPU = config.get("use_gpu")
FORCE_MPS = config.get("force_mps")
SPOKEN_LANGUAGE = config.get("spoken_language")
TARGET_LANGUAGE = config.get("target_language")

# État de la transcription
TRANSCRIPTION_ACTIVE = False
AUDIO_LOOP_RUNNING = False
audio_task = None  # initialisation sécurisée

audio_queue = queue.Queue()

# ----------------------
# Détection GPU
# ----------------------
def detect_gpu_device():
    """Détecte le type de GPU disponible"""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            if FORCE_MPS:
                print("⚠️ MPS forcé (peut causer des erreurs avec Whisper)")
                return "mps"
            else:
                print("⚠️ MPS détecté mais désactivé pour Whisper (problèmes de compatibilité)")
                return "cpu"
        else:
            return "cpu"
    except ImportError:
        return "cpu"

# ----------------------
# INIT Whisper
# ----------------------
print(f"Loading Whisper model '{MODEL_NAME}'...")
gpu_device = detect_gpu_device()
print(f"🔍 GPU détecté: {gpu_device.upper()}")

if gpu_device == "cuda":
    try:
        import torch
        print(f"   - Nom: {torch.cuda.get_device_name(0)}")
        print(f"   - Mémoire: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    except Exception:
        pass
elif gpu_device == "mps":
    print("   - Metal Performance Shaders (Mac)")

if USE_GPU and gpu_device != "cpu":
    try:
        model = whisper.load_model(MODEL_NAME, device=gpu_device)
        print(f"✅ Whisper loaded on {gpu_device}")
    except Exception as e:
        print(f"⚠️ Impossible de charger Whisper sur {gpu_device}: {e}\nFallback to CPU")
        model = whisper.load_model(MODEL_NAME, device="cpu")
else:
    model = whisper.load_model(MODEL_NAME, device="cpu")
    print("💻 Whisper loaded on CPU")

# ----------------------
# MarianMT / M2M100 translator
# ----------------------
translator_enabled = False
translator_device = "cuda" if gpu_device == "cuda" else "cpu"
translator_model_name = f"Helsinki-NLP/opus-mt-{SPOKEN_LANGUAGE}-{TARGET_LANGUAGE}"

try:
    from transformers import MarianMTModel, MarianTokenizer
    translator_tokenizer = MarianTokenizer.from_pretrained(translator_model_name)
    translator_model = MarianMTModel.from_pretrained(translator_model_name).to(translator_device)
    translator_enabled = True
    print(f"✅ Translator loaded: {translator_model_name} on {translator_device}")
except Exception as e:
    print(f"⚠️ Translator not available: {e}")
    translator_enabled = False

def translate_sync(text: str, src_lang: str, tgt_lang: str) -> str:
    """Blocant: traduit text src->tgt avec M2M100"""
    if not translator_enabled:
        return "[TRANSLATOR NOT AVAILABLE]"
    try:
        translator_tokenizer.src_lang = src_lang
        encoded = translator_tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(translator_device)
        forced_id = translator_tokenizer.get_lang_id(tgt_lang)
        generated_tokens = translator_model.generate(**encoded, forced_bos_token_id=forced_id, max_length=512)
        return translator_tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
    except Exception as e:
        return f"[TRANSLATION ERROR: {e}]"

# ----------------------
# SOCKET.IO
# ----------------------
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
app_sio = socketio.ASGIApp(sio, app)

# ----------------------
# Fonctions utilitaires
# ----------------------
def callback(indata, frames, time, status):
    if status:
        asyncio.create_task(send_log(f"⚠️ Audio status: {status}"))
    audio_queue.put(indata.copy())

def validate_microphone_id(mic_id):
    try:
        devices = sd.query_devices()
        return 0 <= mic_id < len(devices) and devices[mic_id]['max_input_channels'] > 0
    except Exception:
        return False

def has_speech(audio):
    rms = np.sqrt(np.mean(np.square(audio)))
    return rms > VOLUME_THRESHOLD

async def send_log(message: str):
    print(message, flush=True)
    await sio.emit('logs', {'message': message})

def get_available_microphones():
    try:
        devices = sd.query_devices()
        return [
            {'id': i, 'name': d['name'], 'channels': d['max_input_channels'], 'sample_rate': d['default_samplerate']}
            for i, d in enumerate(devices) if d['max_input_channels'] > 0
        ]
    except Exception as e:
        print(f"Erreur lors de la récupération des microphones: {e}")
        return []

# ----------------------
# Loop audio principale
# ----------------------
async def audio_loop():
    global TRANSCRIPTION_ACTIVE, AUDIO_LOOP_RUNNING
    buffer = np.zeros((0, 1), dtype=np.float32)
    AUDIO_LOOP_RUNNING = True
    
    print("🎙️ Boucle audio démarrée, en attente du microphone...")
    try:
        while SELECTED_MICROPHONE_ID is None:
            await asyncio.sleep(1)
        print(f"🎙️ Utilisation du microphone ID {SELECTED_MICROPHONE_ID}")
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=callback,
            device=SELECTED_MICROPHONE_ID
        ):
            print("🎙️ Micro OK ! Prêt à traduire...")
            while True:
                try:
                    data = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                buffer = np.concatenate([buffer, data])
                duration = len(buffer) / SAMPLE_RATE
                rms = np.sqrt(np.mean(np.square(buffer.flatten())))

                if duration >= CHUNK_DURATION:
                    audio_data = buffer.flatten()
                    if not has_speech(audio_data):
                        if TRANSCRIPTION_ACTIVE:
                            await send_log("🔇 Silence détecté, chunk ignoré")
                        buffer = np.zeros((0, 1), dtype=np.float32)
                        continue

                    if TRANSCRIPTION_ACTIVE:
                        await send_log("⏳ Processing chunk (transcription)...")
                        try:
                            result = model.transcribe(audio_data, task="transcribe", language=SPOKEN_LANGUAGE, fp16=False)
                            source_text = result.get("text", "").strip()
                        except Exception as e:
                            await send_log(f"❌ Whisper transcription error: {e}")
                            source_text = ""

                        if source_text:
                            await send_log(f"📝 Transcription ({SPOKEN_LANGUAGE}): {source_text}")
                            if translator_enabled:
                                await send_log("🔁 Traduction via M2M100 en cours...")
                                loop = asyncio.get_running_loop()
                                translated_text = await loop.run_in_executor(None, translate_sync, source_text, SPOKEN_LANGUAGE, TARGET_LANGUAGE)
                                await send_log(f"💬 Original ({SPOKEN_LANGUAGE}): {source_text}")
                                await send_log(f"💬 Traduction ({TARGET_LANGUAGE}): {translated_text}")
                                await sio.emit('translation', {'text': translated_text})
                            else:
                                await send_log("⚠️ Traduction locale non disponible — envoi de la transcription brute")
                                await sio.emit('translation', {'text': source_text})
                        else:
                            await send_log("⚠️ Pas de texte extrait par Whisper pour ce chunk")
                    buffer = np.zeros((0, 1), dtype=np.float32)
    except asyncio.CancelledError:
        print("🎙️ Boucle audio annulée")
        raise
    except Exception as e:
        print(f"❌ Erreur dans la boucle audio: {e}")
    finally:
        print("🎙️ Boucle audio arrêtée")
        AUDIO_LOOP_RUNNING = False

# ----------------------
# SOCKET.IO EVENTS
# ----------------------
@sio.event
async def connect(sid, environ):
    print(f"✅ Client connecté: {sid}")
    await send_log(f"✅ Nouveau client connecté: {sid}")
    await sio.emit('config', config, room=sid)

@sio.event
async def disconnect(sid):
    print(f"❌ Client déconnecté: {sid}")
    await send_log(f"❌ Client déconnecté: {sid}")

@sio.event
async def ping(sid, data):
    timestamp = data.get('timestamp', 0)
    await sio.emit('pong', {'timestamp': timestamp}, room=sid)
    await send_log(f"🏓 Ping reçu de {sid}, pong envoyé")

@sio.event
async def get_microphones(sid):
    await send_log("🎤 Récupération de la liste des microphones...")
    microphones = get_available_microphones()
    await sio.emit('microphones', {'microphones': microphones, 'count': len(microphones)}, room=sid)
    await send_log(f"🎤 {len(microphones)} microphone(s) trouvé(s)")

@sio.event
async def set_microphone(sid, data):
    global SELECTED_MICROPHONE_ID, config
    mic_id = data.get('id')
    if mic_id is None or not validate_microphone_id(mic_id):
        await send_log(f"❌ Microphone ID invalide")
        return
    SELECTED_MICROPHONE_ID = mic_id
    config["selected_microphone_id"] = mic_id
    save_config(config)
    await send_log(f"🎤 Microphone sélectionné ID: {mic_id}, config sauvegardée")

@sio.event
async def update_config(sid, data):
    global config, VOLUME_THRESHOLD, CHUNK_DURATION, SPOKEN_LANGUAGE, TARGET_LANGUAGE, SAMPLE_RATE, MODEL_NAME, USE_GPU
    updated = False
    for key in ['volume_threshold','chunk_duration','sample_rate','model_name','use_gpu','spoken_language','target_language']:
        if key in data:
            config[key] = data[key]
            updated = True
            locals()[key.upper()] = data[key] if key not in ['use_gpu','model_name'] else data[key]
            await send_log(f"🔊 {key} mis à jour: {data[key]}")
    if updated:
        save_config(config)
        await send_log("💾 Configuration sauvegardée")

@sio.event
async def start_translation(sid):
    global TRANSCRIPTION_ACTIVE, audio_task
    if SELECTED_MICROPHONE_ID is None:
        await send_log("❌ Aucun microphone sélectionné")
        await sio.emit('translation_status', {'active': False, 'error': 'No microphone selected'}, room=sid)
        return
    TRANSCRIPTION_ACTIVE = True
    if audio_task is None or audio_task.done():
        audio_task = asyncio.create_task(audio_loop())
    await send_log("🎤 Transcription démarrée")
    await sio.emit('translation_status', {'active': True, 'message': 'Transcription started'}, room=sid)

@sio.event
async def stop_translation(sid):
    global TRANSCRIPTION_ACTIVE, AUDIO_LOOP_RUNNING, audio_task
    print("⏹️ Arrêt de la transcription demandé...")
    TRANSCRIPTION_ACTIVE = False
    AUDIO_LOOP_RUNNING = False
    if audio_task and not audio_task.done():
        audio_task.cancel()
        try: await audio_task
        except asyncio.CancelledError: pass
    while not audio_queue.empty():
        try: audio_queue.get_nowait()
        except queue.Empty: break
    await send_log("⏹️ Transcription arrêtée")
    await sio.emit('translation_status', {'active': False, 'message': 'Transcription stopped'})

# ----------------------
# ROUTES HTTP
# ----------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Socket.IO STT server running"}

# ----------------------
# Lancer le serveur
# ----------------------
if __name__ == "__main__":
    print("🚀 Lancement du front Next.js...")
    if platform.system() == "Windows":
        npm_cmd = "npm.cmd run dev"
        next_process = subprocess.Popen(npm_cmd, cwd=FRONT_DIR, shell=True)
    else:
        next_process = subprocess.Popen(["npm","run","dev"], cwd=FRONT_DIR, preexec_fn=os.setsid)

    def shutdown_handler(sig, frame):
        print("\n🛑 Arrêt en cours... (backend + Next.js)")
        kill_process_tree(next_process)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print("⏳ Attente du front (3s)...")
    time.sleep(3)
    print(f"🌍 Ouverture du navigateur sur {FRONT_URL}")
    webbrowser.open(FRONT_URL)

    uvicorn.run(app_sio, host="0.0.0.0", port=8000, log_level="info", access_log=False, loop="asyncio")
