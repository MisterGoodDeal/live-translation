#!/usr/bin/env python3
"""
Script d'installation automatique de PyTorch avec support GPU
Détecte automatiquement le type de machine et installe la bonne version
"""

import subprocess
import sys
import platform
import os

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} réussi")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} échoué: {e}")
        print(f"   Erreur: {e.stderr}")
        return False

def detect_gpu_type():
    """Détecte le type de GPU disponible"""
    print("🔍 Détection du type de GPU...")
    
    # Vérifier si on est sur Mac
    if platform.system() == "Darwin":
        # Vérifier si c'est Apple Silicon
        try:
            result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
            if "arm" in result.stdout.lower():
                print("🍎 Apple Silicon détecté (M1/M2/M3)")
                return "mps"
        except:
            pass
        print("🍎 Mac Intel détecté")
        return "cpu"
    
    # Vérifier CUDA sur Windows/Linux
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            print("🎮 NVIDIA GPU détecté")
            return "cuda"
    except FileNotFoundError:
        pass
    
    print("💻 Aucun GPU détecté")
    return "cpu"

def install_pytorch_gpu(gpu_type):
    """Installe PyTorch avec support GPU selon le type détecté"""
    
    if gpu_type == "cuda":
        print("🎮 Installation de PyTorch avec support CUDA...")
        commands = [
            "pip uninstall torch torchvision torchaudio -y",
            "pip install torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118 --index-url https://download.pytorch.org/whl/cu118"
        ]
        
    elif gpu_type == "mps":
        print("🍎 Installation de PyTorch avec support Metal (MPS)...")
        commands = [
            "pip uninstall torch torchvision torchaudio -y",
            "pip install torch torchvision torchaudio"
        ]
        
    else:  # cpu
        print("💻 Installation de PyTorch CPU...")
        commands = [
            "pip uninstall torch torchvision torchaudio -y",
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"
        ]
    
    # Exécuter les commandes
    for command in commands:
        if not run_command(command, f"Exécution: {command}"):
            return False
    
    return True

def verify_installation():
    """Vérifie que l'installation GPU fonctionne"""
    print("🔍 Vérification de l'installation...")
    
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"🎮 CUDA disponible: {torch.cuda.get_device_name(0)}")
            print(f"   Mémoire: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("🍎 Metal Performance Shaders (MPS) disponible")
        else:
            print("💻 Mode CPU uniquement")
            
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import PyTorch: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Installation automatique de PyTorch avec support GPU")
    print("=" * 60)
    
    # Détecter le type de GPU
    gpu_type = detect_gpu_type()
    
    # Installer PyTorch
    if install_pytorch_gpu(gpu_type):
        print("\n✅ Installation terminée avec succès!")
        
        # Vérifier l'installation
        if verify_installation():
            print("\n🎉 PyTorch est prêt à utiliser le GPU!")
        else:
            print("\n⚠️ Installation terminée mais vérification échouée")
    else:
        print("\n❌ Installation échouée")
        sys.exit(1)

if __name__ == "__main__":
    main()
