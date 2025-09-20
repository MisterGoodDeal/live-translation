#!/usr/bin/env python3
"""
Script de lancement complet - Exécute tous les scripts dans l'ordre
"""

import subprocess
import sys
import os

def run_script(script_name, description):
    """Exécute un script Python"""
    print(f"\n{'='*50}")
    print(f"🔄 {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {description} - Terminé")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Live Translation - Installation et Lancement Complet")
    print("=" * 60)
    
    scripts = [
        ("install_python.py", "Installation des dépendances Python"),
        ("build_nextjs.py", "Build du projet Next.js"),
        ("start_server.py", "Démarrage du serveur")
    ]
    
    for script, description in scripts:
        if not run_script(script, description):
            print(f"\n❌ Arrêt à l'étape: {description}")
            print("💡 Vérifiez les erreurs ci-dessus et relancez le script")
            return False
    
    print("\n🎉 Tous les scripts ont été exécutés avec succès!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
