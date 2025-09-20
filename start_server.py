#!/usr/bin/env python3
"""
Script de démarrage du serveur Python
"""

import subprocess
import sys
import os
import time
import webbrowser
import platform
import signal
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

# Configuration
FRONTEND_PORT = 3000
BACKEND_PORT = 8000
FRONTEND_BUILD_DIR = "live-translation-front/out"

def check_build_exists():
    """Vérifie que le build Next.js existe"""
    out_dir = Path(FRONTEND_BUILD_DIR)
    if not out_dir.exists():
        print("❌ Build Next.js non trouvé")
        print("💡 Exécutez d'abord: python build_nextjs.py")
        return False
    
    index_file = out_dir / "index.html"
    if not index_file.exists():
        print("❌ index.html non trouvé dans le build")
        print("💡 Exécutez d'abord: python build_nextjs.py")
        return False
    
    print("✅ Build Next.js trouvé")
    return True

def check_python_env():
    """Vérifie l'environnement Python"""
    if not os.path.exists(".venv"):
        print("❌ Environnement virtuel non trouvé")
        print("💡 Exécutez d'abord: python install_python.py")
        return False
    
    print("✅ Environnement virtuel trouvé")
    return True

def get_python_cmd():
    """Retourne la commande Python selon l'OS"""
    if platform.system() == "Windows":
        return ".venv\\Scripts\\python"
    else:
        return ".venv/bin/python"

def start_backend():
    """Démarre le serveur backend Python"""
    python_cmd = get_python_cmd()
    
    print(f"🐍 Démarrage du serveur backend...")
    print(f"🔌 Socket.IO: http://localhost:{BACKEND_PORT}")
    
    try:
        # Lancer le serveur backend
        subprocess.run([python_cmd, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur serveur backend: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur...")
        return True

def main():
    """Fonction principale"""
    print("🚀 Démarrage du serveur Live Translation")
    print("=" * 40)
    
    # Vérifications préliminaires
    if not check_python_env():
        return False
    
    if not check_build_exists():
        return False
    
    # Afficher les URLs
    print("\n" + "=" * 50)
    print(f"📱 Interface principale: http://localhost:{FRONTEND_PORT}")
    print(f"🎬 Interface sous-titres: http://localhost:{FRONTEND_PORT}/captions")
    print(f"🔌 Backend Socket.IO: http://localhost:{BACKEND_PORT}")
    print("=" * 50)
    print("💡 Appuyez sur Ctrl+C pour arrêter")
    print()
    
    # Démarrer le serveur backend (bloquant)
    return start_backend()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
        sys.exit(0)
