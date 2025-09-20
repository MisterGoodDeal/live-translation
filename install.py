#!/usr/bin/env python3
"""
Script d'installation automatique complet
Installe toutes les dépendances et configure le support GPU
"""

import subprocess
import sys
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
        return False

def main():
    """Fonction principale d'installation"""
    print("🚀 Installation automatique du système de traduction en temps réel")
    print("=" * 70)
    
    # Vérifier si on est dans un environnement virtuel
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Attention: Il est recommandé d'utiliser un environnement virtuel")
        print("   Créez-en un avec: python -m venv .venv")
        print("   Puis activez-le: source .venv/bin/activate (Mac/Linux) ou .venv\\Scripts\\activate (Windows)")
        response = input("Continuer quand même? (y/N): ")
        if response.lower() != 'y':
            print("Installation annulée")
            sys.exit(1)
    
    # 1. Installer les dépendances de base
    print("\n📦 Installation des dépendances de base...")
    if not run_command("pip install -r requirements.txt", "Installation des dépendances"):
        print("❌ Échec de l'installation des dépendances de base")
        sys.exit(1)
    
    # 2. Installer PyTorch avec support GPU
    print("\n🎮 Configuration du support GPU...")
    if not run_command("python install_gpu.py", "Installation PyTorch GPU"):
        print("❌ Échec de l'installation GPU")
        sys.exit(1)
    
    # 3. Vérifier l'installation
    print("\n🔍 Vérification finale...")
    if run_command("python -c \"import whisper, sounddevice, fastapi, socketio; print('✅ Toutes les dépendances sont installées')\"", "Vérification des imports"):
        print("\n🎉 Installation terminée avec succès!")
        print("\n📋 Prochaines étapes:")
        print("   1. Lancez le serveur: python main.py")
        print("   2. Ouvrez http://localhost:3000 dans votre navigateur")
        print("   3. Configurez votre microphone et activez le GPU si souhaité")
    else:
        print("\n❌ Vérification échouée - certaines dépendances manquent")

if __name__ == "__main__":
    main()
