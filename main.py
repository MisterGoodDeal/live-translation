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

# ----------------------
# CONFIG
# ----------------------
CONFIG_FILE = "config.json"
FRONT_URL = "http://localhost:3000"

# Configuration par défaut
DEFAULT_CONFIG = {
    "model_name": "small",
    "sample_rate": 16000,
    "chunk_duration": 2,
    "volume_threshold": 0.01,
    "selected_microphone_id": None,
    "use_gpu": False,
    "force_mps": False  # Option pour forcer MPS sur Mac (peut causer des erreurs)
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
MODEL_NAME = config["model_name"]
SAMPLE_RATE = config["sample_rate"]
CHUNK_DURATION = config["chunk_duration"]
VOLUME_THRESHOLD = config["volume_threshold"]
SELECTED_MICROPHONE_ID = config["selected_microphone_id"]
USE_GPU = config["use_gpu"]
FORCE_MPS = config.get("force_mps", False)

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
                # MPS a des problèmes de compatibilité avec Whisper
                # On force le CPU pour Mac pour éviter les erreurs
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

# Afficher les informations GPU
gpu_device = detect_gpu_device()
print(f"🔍 GPU détecté: {gpu_device.upper()}")
if gpu_device == "cuda":
    try:
        import torch
        print(f"   - Nom: {torch.cuda.get_device_name(0)}")
        print(f"   - Mémoire: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    except:
        pass
elif gpu_device == "mps":
    print("   - Metal Performance Shaders (Mac)")

if USE_GPU:
    print(f"🎮 Configuration GPU: {'Activé' if USE_GPU else 'Désactivé'}")
    
    if gpu_device != "cpu":
        print(f"🎮 Tentative de chargement avec accélération {gpu_device.upper()}...")
        try:
            model = whisper.load_model(MODEL_NAME, device=gpu_device)
            print(f"✅ Modèle chargé avec succès sur {gpu_device.upper()}")
        except Exception as e:
            print(f"⚠️ Impossible de charger sur {gpu_device.upper()}: {e}")
            print("🔄 Fallback vers CPU...")
            model = whisper.load_model(MODEL_NAME, device="cpu")
            print("✅ Modèle chargé sur CPU")
    else:
        print("⚠️ Aucun GPU détecté, utilisation du CPU")
        model = whisper.load_model(MODEL_NAME, device="cpu")
        print("💻 Modèle chargé sur CPU")
else:
    model = whisper.load_model(MODEL_NAME, device="cpu")
    print("💻 Modèle chargé sur CPU")

audio_queue = queue.Queue()

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
                    await send_log(f"Buffer: {duration:.2f}s | RMS: {rms:.4f}")

                if duration >= CHUNK_DURATION:
                    audio_data = buffer.flatten()

                    if not has_speech(audio_data):
                        if TRANSCRIPTION_ACTIVE:
                            await send_log("🔇 Silence détecté, chunk ignoré")
                        buffer = np.zeros((0, 1), dtype=np.float32)
                        continue

                    # Traiter seulement si la transcription est active
                    if TRANSCRIPTION_ACTIVE:
                        await send_log("⏳ Processing chunk...")
                        result = model.transcribe(
                            audio_data,
                            task="translate",
                            language="fr",
                            fp16=False
                        )

                        translated_text = result["text"].strip()
                        if translated_text:  # Envoyer seulement si il y a du texte
                            await send_log(f"💬 Traduction: {translated_text}")
                            # envoyer la traduction à tous les clients
                            await sio.emit('translation', {'text': translated_text})

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
        'model_name': config['model_name'],
        'sample_rate': config['sample_rate'],
        'chunk_duration': config['chunk_duration'],
        'volume_threshold': config['volume_threshold'],
        'selected_microphone_id': config['selected_microphone_id'],
        'use_gpu': config['use_gpu']
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
    global config, VOLUME_THRESHOLD, CHUNK_DURATION
    
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
        await send_log(f"🔊 Modèle Whisper mise à jour: {MODEL_NAME}")
        updated = True

    if 'use_gpu' in data:
        config["use_gpu"] = bool(data['use_gpu'])
        USE_GPU = config["use_gpu"]
        await send_log(f"🎮 Utilisation GPU mise à jour: {'Activé' if USE_GPU else 'Désactivé'}")
        await send_log("⚠️ Redémarrez l'application pour que les changements GPU prennent effet")
        updated = True
    
    if updated:
        save_config(config)
        await send_log("💾 Configuration sauvegardée")

@sio.event
async def get_config(sid):
    """Récupère la configuration actuelle"""
    await sio.emit('config', {
        'model_name': config["model_name"],
        'sample_rate': config["sample_rate"],
        'chunk_duration': config["chunk_duration"],
        'volume_threshold': config["volume_threshold"],
        'selected_microphone_id': config["selected_microphone_id"],
        'use_gpu': config["use_gpu"]
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
    print("🚀 Lancement du front Next.js...")
    next_process = subprocess.Popen(
        ["npm", "run", "start"],
        cwd="live-translation-front",
        preexec_fn=os.setsid if platform.system() != "Windows" else None
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
