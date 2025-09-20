#!/usr/bin/env python3
"""
Script d'installation des dépendances Python
"""

import subprocess
import sys
import os
import platform

def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur: {e.stderr}")
        return False

def check_python():
    """Vérifie la version de Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro} détecté")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ requis")
        return False
    
    print("✅ Version Python compatible")
    return True

def create_virtual_env():
    """Crée un environnement virtuel"""
    if os.path.exists(".venv"):
        print("📁 Environnement virtuel existant trouvé")
        return True
    
    return run_command("python -m venv .venv", "Création de l'environnement virtuel")

def activate_and_install():
    """Active l'environnement virtuel et installe les dépendances"""
    if platform.system() == "Windows":
        activate_cmd = ".venv\\Scripts\\activate"
        pip_cmd = ".venv\\Scripts\\pip"
    else:
        activate_cmd = "source .venv/bin/activate"
        pip_cmd = ".venv/bin/pip"
    
    # Mettre à jour pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Mise à jour de pip"):
        return False
    
    # Installer les dépendances de base
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installation des dépendances Python"):
        return False
    
    return True

def install_gpu_support():
    """Installe le support GPU si disponible"""
    print("🎮 Vérification du support GPU...")
    
    try:
        import torch
        if torch.cuda.is_available():
            print("✅ CUDA détecté - Support GPU déjà installé")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("✅ MPS détecté (Mac) - Support GPU déjà installé")
        else:
            print("💻 Aucun GPU détecté - Utilisation CPU uniquement")
    except ImportError:
        print("⚠️ PyTorch non installé - Installation du support GPU...")
        
        if platform.system() == "Windows":
            # Windows - CUDA
            run_command(".venv\\Scripts\\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118", "Installation PyTorch CUDA")
        else:
            # Mac/Linux - MPS/CPU
            run_command(".venv/bin/pip install torch torchvision torchaudio", "Installation PyTorch")

def main():
    """Fonction principale"""
    print("🚀 Installation des dépendances Python")
    print("=" * 40)
    
    # Vérifier Python
    if not check_python():
        return False
    
    # Créer l'environnement virtuel
    if not create_virtual_env():
        return False
    
    # Installer les dépendances
    if not activate_and_install():
        return False
    
    # Installer le support GPU
    install_gpu_support()
    
    print("\n🎉 Installation terminée avec succès!")
    print("📋 Prochaines étapes:")
    print("   1. python build_nextjs.py")
    print("   2. python start_server.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
