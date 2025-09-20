#!/usr/bin/env python3
"""
Script de démarrage complet du serveur Live Translation
- Backend Python (Socket.IO)
- Frontend Next.js
- Ouverture automatique des pages dans le navigateur
Compatible Windows / macOS / Linux
"""

import subprocess
import sys
import os
import time
import webbrowser
import platform
import signal
from pathlib import Path

# Configuration
FRONTEND_PORT = 3000
BACKEND_PORT = 8000
FRONTEND_DIR = "live-translation-front"
BACKEND_SCRIPT = "main.py"

# ==========================
# Helpers
# ==========================
def get_python_cmd():
    """Retourne la commande Python selon l'OS"""
    if platform.system() == "Windows":
        return ".venv\\Scripts\\python"
    else:
        return ".venv/bin/python"

def check_python_env():
    if not os.path.exists(".venv"):
        print("❌ Environnement virtuel non trouvé")
        print("💡 Exécutez d'abord: python install_python.py")
        return False
    print("✅ Environnement virtuel trouvé")
    return True

# ==========================
# Lancement des serveurs
# ==========================
def start_backend():
    """Démarre le serveur backend Python"""
    python_cmd = get_python_cmd()
    print(f"🐍 Démarrage du serveur backend...")
    print(f"🔌 Socket.IO: http://localhost:{BACKEND_PORT}")

    # On lance le backend en subprocess pour pouvoir le kill proprement
    return subprocess.Popen([python_cmd, BACKEND_SCRIPT])

    """Démarre le frontend Next.js"""
    print("🚀 Lancement du front Next.js...")

    try:
        if platform.system() == "Windows":
            # Sur Windows, utiliser le npm.cmd
            npm_cmd = "npm.cmd run start"
            next_process = subprocess.Popen(
                npm_cmd,
                cwd=FRONTEND_DIR,
                shell=True
            )
        else:
            # macOS / Linux
            next_process = subprocess.Popen(
                ["npm", "run", "start"],
                cwd=FRONTEND_DIR,
                preexec_fn=os.setsid
            )
        print("✅ Serveur Next.js démarré")
        return next_process
    except FileNotFoundError:
        print("❌ npm non trouvé. Assurez-vous qu'il est installé et dans votre PATH")
        return None

# ==========================
# Kill propre des processus
# ==========================
def kill_process(proc):
    """Tue un subprocess proprement"""
    if proc and proc.poll() is None:
        try:
            if platform.system() == "Windows":
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception as e:
            print(f"⚠️ Erreur en tuant le processus: {e}")

# ==========================
# Fonction principale
# ==========================
def main():
    # Vérifications préliminaires
    if not check_python_env():
        return False

    # Affichage des URLs
    print("\n" + "=" * 50)
    print(f"📱 Interface principale: http://localhost:{FRONTEND_PORT}")
    print(f"🎬 Interface sous-titres: http://localhost:{FRONTEND_PORT}/captions")
    print(f"🔌 Backend Socket.IO: http://localhost:{BACKEND_PORT}")
    print("=" * 50)
    print("💡 Appuyez sur Ctrl+C pour arrêter\n")

    # Démarrage backend + frontend
    backend_proc = start_backend()
    # Petit délai pour laisser Next.js démarrer avant d'ouvrir le navigateur
    time.sleep(5)
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}/captions")

    try:
        # Attendre que le backend se termine
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
        kill_process(backend_proc)
        print("✅ Tous les serveurs arrêtés")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
