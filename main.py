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
    "force_mps": False,  # Option pour forcer MPS sur Mac (peut causer des erreurs)
    "spoken_language": "en",   # langue parlée (ex: "en")
    "target_language": "fr"    # langue cible de traduction (ex: "fr")
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
    """Charge la configuration depuis le fichier JSON"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Configuration chargée depuis {CONFIG_FILE}")
                return config
        except Exception as e:
            print(f"❌ Erreur lors du chargement de la config: {e}")
    
    print(f"📝 Création de la configuration par défaut")
    return DEFAULT_CONFIG.copy()

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
MODEL_NAME = config.get("model_name", DEFAULT_CONFIG["model_name"])
SAMPLE_RATE = config.get("sample_rate", DEFAULT_CONFIG["sample_rate"])
CHUNK_DURATION = config.get("chunk_duration", DEFAULT_CONFIG["chunk_duration"])
VOLUME_THRESHOLD = config.get("volume_threshold", DEFAULT_CONFIG["volume_threshold"])
SELECTED_MICROPHONE_ID = config.get("selected_microphone_id", DEFAULT_CONFIG["selected_microphone_id"])
USE_GPU = config.get("use_gpu", DEFAULT_CONFIG["use_gpu"])
FORCE_MPS = config.get("force_mps", DEFAULT_CONFIG["force_mps"])
SPOKEN_LANGUAGE = config.get("spoken_language", DEFAULT_CONFIG["spoken_language"])
TARGET_LANGUAGE = config.get("target_language", DEFAULT_CONFIG["target_language"])

# État de la transcription
TRANSCRIPTION_ACTIVE = False
AUDIO_LOOP_RUNNING = False

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
# INIT Whisper (unchanged)
# ----------------------
print(f"Loading Whisper model '{MODEL_NAME}'...")

# Afficher les informations GPU
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

# Charger Whisper sur gpu_device si use_gpu True
if USE_GPU:
    if gpu_device != "cpu":
        try:
            model = whisper.load_model(MODEL_NAME, device=gpu_device)
            print(f"✅ Whisper loaded on {gpu_device}")
        except Exception as e:
            print(f"⚠️ Impossible de charger Whisper sur {gpu_device}: {e}\nFallback to CPU")
            model = whisper.load_model(MODEL_NAME, device="cpu")
    else:
        print("⚠️ Aucun GPU détecté, utilisation du CPU pour Whisper")
        model = whisper.load_model(MODEL_NAME, device="cpu")
else:
    model = whisper.load_model(MODEL_NAME, device="cpu")
    print("💻 Whisper loaded on CPU")

audio_queue = queue.Queue()

# ----------------------
# M2M100 translator (HuggingFace) initialization
# ----------------------
translator_enabled = False
translator_device = "cpu"
translator_model_name = "facebook/m2m100_418M"  # choix raisonnable

try:
    from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
    import torch as _torch
    # choose device for translator
    if _torch.cuda.is_available():
        translator_device = "cuda"
    else:
        translator_device = "cpu"
    print(f"🔍 Translator device: {translator_device}")

    print(f"📥 Loading translator model '{translator_model_name}' (this may take time)...")
    translator_tokenizer = M2M100Tokenizer.from_pretrained(translator_model_name)
    translator_model = M2M100ForConditionalGeneration.from_pretrained(translator_model_name)
    translator_model.to(translator_device)
    translator_enabled = True
    print("✅ Translator model loaded")
except Exception as e:
    translator_enabled = False
    print(f"⚠️ Translator not available: {e}")
    print("   -> Install transformers & sentencepiece and ensure CUDA-compatible torch if you want GPU translation.")
    # keep going without translator

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
    """Valide qu'un microphone ID existe"""
    try:
        devices = sd.query_devices()
        if 0 <= mic_id < len(devices) and devices[mic_id]['max_input_channels'] > 0:
            return True
        return False
    except Exception:
        return False

def has_speech(audio):
    rms = np.sqrt(np.mean(np.square(audio)))
    return rms > VOLUME_THRESHOLD

async def send_log(message: str):
    print(message, flush=True)
    await sio.emit('logs', {'message': message})

def get_available_microphones():
    """Récupère la liste des microphones disponibles"""
    try:
        devices = sd.query_devices()
        microphones = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # C'est un périphérique d'entrée
                microphones.append({
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        
        return microphones
    except Exception as e:
        print(f"Erreur lors de la récupération des microphones: {e}")
        return []

# ----------------------
# Translator helper (blocking) - run in executor
# ----------------------
def translate_sync(text: str, src_lang: str, tgt_lang: str) -> str:
    """Blocant: traduit text src->tgt avec M2M100"""
    if not translator_enabled:
        return "[TRANSLATOR NOT AVAILABLE]"
    # tokenizer expects language codes like "en", "fr"
    try:
        translator_tokenizer.src_lang = src_lang
        encoded = translator_tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(translator_device)
        forced_id = translator_tokenizer.get_lang_id(tgt_lang)
        generated_tokens = translator_model.generate(**encoded, forced_bos_token_id=forced_id, max_length=512)
        out = translator_tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
        return out
    except Exception as e:
        return f"[TRANSLATION ERROR: {e}]"

# ----------------------
# Loop audio principale
# ----------------------
async def audio_loop():
    global TRANSCRIPTION_ACTIVE, AUDIO_LOOP_RUNNING
    buffer = np.zeros((0, 1), dtype=np.float32)
    
    print("🎙️ Boucle audio démarrée, en attente du microphone...")
    AUDIO_LOOP_RUNNING = True
    
    try:
        # Attendre qu'un microphone soit sélectionné
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
                    # Utiliser un timeout plus court pour être plus réactif
                    data = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                buffer = np.concatenate([buffer, data])
                duration = len(buffer) / SAMPLE_RATE
                rms = np.sqrt(np.mean(np.square(buffer.flatten())))
                
                # Afficher les logs seulement si la transcription est active et qu'il y a de l'activité
                if TRANSCRIPTION_ACTIVE and rms > VOLUME_THRESHOLD:

                if duration >= CHUNK_DURATION:
                    audio_data = buffer.flatten()

                    if not has_speech(audio_data):
                        if TRANSCRIPTION_ACTIVE:
                            await send_log("🔇 Silence détecté, chunk ignoré")
                        buffer = np.zeros((0, 1), dtype=np.float32)
                        continue

                    # Traiter seulement si la transcription est active
                    if TRANSCRIPTION_ACTIVE:
                        await send_log("⏳ Processing chunk (transcription)...")

                        # 1) Transcrire (Whisper) — on transcrit dans la langue parlée (ex: "en")
                        try:
                            # task="transcribe" so whisper returns text in source language
                            result = model.transcribe(
                                audio_data,
                                task="transcribe",
                                language=SPOKEN_LANGUAGE,
                                fp16=False
                            )
                            source_text = result.get("text", "").strip()
                        except Exception as e:
                            await send_log(f"❌ Whisper transcription error: {e}")
                            source_text = ""

                        if source_text:
                            await send_log(f"📝 Transcription ({SPOKEN_LANGUAGE}): {source_text}")

                            # 2) Traduire localement via M2M100 (si activé)
                            if translator_enabled:
                                await send_log("🔁 Traduction via M2M100 en cours...")
                                loop = asyncio.get_running_loop()
                                try:
                                    translated_text = await loop.run_in_executor(
                                        None,
                                        translate_sync,
                                        source_text,
                                        SPOKEN_LANGUAGE,
                                        TARGET_LANGUAGE
                                    )
                                    await send_log(f"💬 Original ({SPOKEN_LANGUAGE}): {source_text}")
                                    await send_log(f"💬 Traduction ({TARGET_LANGUAGE}): {translated_text}")
                                    await sio.emit('translation', {'text': translated_text})
                                except Exception as e:
                                    await send_log(f"❌ Erreur traduction: {e}")
                            else:
                                # si pas de trad local, on peut renvoyer la transcription (ou la marquer)
                                await send_log("⚠️ Traduction locale non disponible — envoi de la transcription brute")
                                await sio.emit('translation', {'text': source_text})
                        else:
                            await send_log("⚠️ Pas de texte extrait par Whisper pour ce chunk")

                    buffer = np.zeros((0, 1), dtype=np.float32)
    except asyncio.CancelledError:
        print("🎙️ Boucle audio annulée")
        raise  # Re-raise pour que la tâche soit marquée comme annulée
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
    
    # Envoyer la configuration actuelle au client
    await sio.emit('config', {
        'model_name': config.get('model_name'),
        'sample_rate': config.get('sample_rate'),
        'chunk_duration': config.get('chunk_duration'),
        'volume_threshold': config.get('volume_threshold'),
        'selected_microphone_id': config.get('selected_microphone_id'),
        'use_gpu': config.get('use_gpu'),
        'spoken_language': config.get('spoken_language'),
        'target_language': config.get('target_language')
    }, room=sid)

@sio.event
async def disconnect(sid):
    print(f"❌ Client déconnecté: {sid}")
    await send_log(f"❌ Client déconnecté: {sid}")

@sio.event
async def ping(sid, data):
    """Répondre au ping du client avec un pong"""
    timestamp = data.get('timestamp', 0)
    await sio.emit('pong', {'timestamp': timestamp}, room=sid)
    await send_log(f"🏓 Ping reçu de {sid}, pong envoyé")

@sio.event
async def get_microphones(sid):
    """Récupère et envoie la liste des microphones disponibles"""
    await send_log("🎤 Récupération de la liste des microphones...")
    microphones = get_available_microphones()
    
    await sio.emit('microphones', {
        'microphones': microphones,
        'count': len(microphones)
    }, room=sid)
    
    await send_log(f"🎤 {len(microphones)} microphone(s) trouvé(s)")
    for mic in microphones:
        await send_log(f"  - {mic['name']} (ID: {mic['id']}, {mic['channels']} canal(s), {mic['sample_rate']}Hz)")

@sio.event
async def set_microphone(sid, data):
    """Configure le microphone sélectionné"""
    global SELECTED_MICROPHONE_ID, config
    
    mic_id = data.get('id')
    if mic_id is None:
        await send_log("❌ ID de microphone manquant")
        return
    
    if not validate_microphone_id(mic_id):
        await send_log(f"❌ Microphone ID {mic_id} invalide")
        return
    
    # Récupérer les infos du microphone
    devices = sd.query_devices()
    mic_info = devices[mic_id]
    
    SELECTED_MICROPHONE_ID = mic_id
    config["selected_microphone_id"] = mic_id
    save_config(config)
    
    await send_log(f"🎤 Microphone sélectionné: {mic_info['name']} (ID: {mic_id})")
    await send_log(f"   - Canaux: {mic_info['max_input_channels']}")
    await send_log(f"   - Fréquence: {mic_info['default_samplerate']}Hz")
    await send_log(f"💾 Configuration sauvegardée")

@sio.event
async def update_config(sid, data):
    """Met à jour la configuration"""
    global config, VOLUME_THRESHOLD, CHUNK_DURATION, SPOKEN_LANGUAGE, TARGET_LANGUAGE, SAMPLE_RATE, MODEL_NAME, USE_GPU
    
    updated = False
    
    if 'volume_threshold' in data:
        config["volume_threshold"] = float(data['volume_threshold'])
        VOLUME_THRESHOLD = config["volume_threshold"]
        await send_log(f"🔊 Seuil de volume mis à jour: {VOLUME_THRESHOLD}")
        updated = True
    
    if 'chunk_duration' in data:
        config["chunk_duration"] = float(data['chunk_duration'])
        CHUNK_DURATION = config["chunk_duration"]
        await send_log(f"⏱️ Durée des chunks mise à jour: {CHUNK_DURATION}s")
        updated = True
    
    if 'sample_rate' in data:
        config["sample_rate"] = int(data['sample_rate'])
        SAMPLE_RATE = config["sample_rate"]
        await send_log(f"🔊 Fréquence d'échantillonnage mise à jour: {SAMPLE_RATE}Hz")
        updated = True

    if 'model_name' in data:
        config["model_name"] = data['model_name']
        MODEL_NAME = config["model_name"]
        await send_log(f"🔊 Modèle Whisper mis à jour: {MODEL_NAME}")
        updated = True

    if 'use_gpu' in data:
        config["use_gpu"] = bool(data['use_gpu'])
        USE_GPU = config["use_gpu"]
        await send_log(f"🎮 Utilisation GPU mise à jour: {'Activé' if USE_GPU else 'Désactivé'}")
        await send_log("⚠️ Redémarrez l'application pour que les changements GPU prennent effet")
        updated = True
    
    if 'spoken_language' in data:
        config["spoken_language"] = data['spoken_language']
        SPOKEN_LANGUAGE = config["spoken_language"]
        await send_log(f"🔊 Langue parlée mise à jour: {SPOKEN_LANGUAGE}")
        updated = True

    if 'target_language' in data:
        config["target_language"] = data['target_language']
        TARGET_LANGUAGE = config["target_language"]
        await send_log(f"🔊 Langue cible mise à jour: {TARGET_LANGUAGE}")
        updated = True
    
    if updated:
        save_config(config)
        await send_log("💾 Configuration sauvegardée")

@sio.event
async def get_config(sid):
    """Récupère la configuration actuelle"""
    await sio.emit('config', {
        'model_name': config.get("model_name"),
        'sample_rate': config.get("sample_rate"),
        'chunk_duration': config.get("chunk_duration"),
        'volume_threshold': config.get("volume_threshold"),
        'selected_microphone_id': config.get("selected_microphone_id"),
        'use_gpu': config.get("use_gpu"),
        'spoken_language': config.get("spoken_language"),
        'target_language': config.get("target_language")
    }, room=sid)

@sio.event
async def start_translation(sid):
    """Démarre la transcription"""
    global TRANSCRIPTION_ACTIVE, audio_task
    
    if SELECTED_MICROPHONE_ID is None:
        await send_log("❌ Aucun microphone sélectionné")
        await sio.emit('translation_status', {'active': False, 'error': 'No microphone selected'}, room=sid)
        return
    
    TRANSCRIPTION_ACTIVE = True
    
    # Démarrer la boucle audio si elle n'est pas déjà démarrée
    if 'audio_task' not in globals() or audio_task.done():
        audio_task = asyncio.create_task(audio_loop())
        print("🎙️ Boucle audio démarrée")
    
    await send_log("🎤 Transcription démarrée")
    await sio.emit('translation_status', {'active': True, 'message': 'Transcription started'}, room=sid)

@sio.event
async def stop_translation(sid):
    """Arrête la transcription"""
    global TRANSCRIPTION_ACTIVE, AUDIO_LOOP_RUNNING, audio_task
    
    print("⏹️ Arrêt de la transcription demandé...")
    TRANSCRIPTION_ACTIVE = False
    AUDIO_LOOP_RUNNING = False
    
    # Arrêter complètement la tâche audio
    if 'audio_task' in globals() and audio_task and not audio_task.done():
        audio_task.cancel()
        try:
            await audio_task
        except asyncio.CancelledError:
            pass
    
    # Vider la queue audio
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break
    
    await send_log("⏹️ Transcription arrêtée")
    await sio.emit('translation_status', {'active': False, 'message': 'Transcription stopped'}, room=sid)
    print("✅ Transcription arrêtée avec succès")

# ----------------------
# ROUTES HTTP
# ----------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Socket.IO STT server running"}

# ----------------------
# Lancer le serveur
# ----------------------
async def main():
    """Fonction principale qui lance le serveur et la boucle audio"""
    # Configurer uvicorn
    config = uvicorn.Config(app_sio, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    
    # Lancer la boucle audio en arrière-plan (sans attendre)
    asyncio.create_task(audio_loop())
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        print("Arrêt du serveur...")

if __name__ == "__main__":
    # Lancer Next.js
    print("🚀 Lancement du front Next.js...")

    if platform.system() == "Windows":
        npm_cmd = "npm.cmd run dev"
        next_process = subprocess.Popen(
            npm_cmd,
            cwd=FRONT_DIR,
            shell=True
        )
    else:
        next_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONT_DIR,
            preexec_fn=os.setsid
        )

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

    # Démarrer le serveur avec une configuration qui gère mieux les interruptions
    uvicorn.run(
        app_sio, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        access_log=False,  # Réduire les logs pour moins de spam
        loop="asyncio"     # Forcer l'utilisation d'asyncio
    )
