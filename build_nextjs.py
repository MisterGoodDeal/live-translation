#!/usr/bin/env python3
"""
Script de build du projet Next.js compatible Windows et macOS/Linux
"""

import subprocess
import sys
import os
from pathlib import Path
import platform

def run_command(cmd, description, cwd=None):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=os.environ
        )
        print(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur:")
        print(e.stderr)
        return False

def is_windows():
    """Retourne True si le système est Windows"""
    return platform.system().lower() == "windows"

def check_node():
    """Vérifie que Node.js est installé"""
    cmd = "node --version"
    if is_windows():
        cmd = "node --version"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=os.environ)
        version = result.stdout.strip()
        print(f"📦 Node.js {version} détecté")
        return True
    except FileNotFoundError:
        print("❌ Node.js non trouvé - Veuillez installer Node.js")
        return False

def check_npm():
    """Vérifie que npm est installé"""
    cmd = "npm --version"
    if is_windows():
        cmd = "npm --version"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=os.environ)
        version = result.stdout.strip()
        print(f"📦 npm {version} détecté")
        return True
    except FileNotFoundError:
        print("❌ npm non trouvé - Veuillez installer npm")
        return False

def check_frontend_dir():
    """Vérifie que le dossier frontend existe"""
    frontend_dir = Path("live-translation-front")
    if not frontend_dir.exists():
        print("❌ Dossier live-translation-front non trouvé")
        return False
    
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("❌ package.json non trouvé dans live-translation-front")
        return False
    
    print("✅ Dossier frontend trouvé")
    return True

def install_dependencies():
    """Installe les dépendances npm"""
    frontend_dir = "live-translation-front"
    
    if os.path.exists(f"{frontend_dir}/node_modules"):
        print("📁 node_modules existant trouvé")
        return True
    
    return run_command("npm install", "Installation des dépendances npm", cwd=frontend_dir)

def verify_build():
    """Vérifie que le build a réussi"""
    out_dir = Path("live-translation-front/out")
    if not out_dir.exists():
        print("❌ Dossier de build 'out' non trouvé")
        return False
    
    index_file = out_dir / "index.html"
    if not index_file.exists():
        print("❌ index.html non trouvé dans le build")
        return False
    
    print("✅ Build vérifié avec succès")
    return True

def main():
    """Fonction principale"""
    print("🔨 Build du projet Next.js")
    print("=" * 30)
    
    # Vérifications préliminaires
    if not check_node():
        return False
    
    if not check_npm():
        return False
    
    if not check_frontend_dir():
        return False
    
    # Installation des dépendances
    if not install_dependencies():
        return False
    
    print("\n🎉 Installation terminée avec succès!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
