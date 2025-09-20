#!/usr/bin/env python3
"""
Script pour créer un raccourci Windows vers Live Translation
"""

import os
import sys
from pathlib import Path

def create_shortcut():
    """Crée un raccourci Windows"""
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("❌ Modules Windows requis non trouvés")
        print("💡 Installez avec: pip install winshell pywin32")
        return False
    
    # Chemin du script batch
    script_path = Path(__file__).parent / "start_live_translation.bat"
    script_path = script_path.resolve()
    
    # Chemin du raccourci sur le bureau
    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, "Live Translation.lnk")
    
    # Créer le raccourci
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = str(script_path)
    shortcut.WorkingDirectory = str(Path(__file__).parent)
    shortcut.Description = "Live Translation WebServer"
    shortcut.IconLocation = str(script_path)  # Utilise l'icône du batch
    shortcut.save()
    
    print(f"✅ Raccourci créé: {shortcut_path}")
    return True

if __name__ == "__main__":
    if sys.platform != "win32":
        print("❌ Ce script fonctionne uniquement sur Windows")
        sys.exit(1)
    
    print("🔗 Création du raccourci Windows...")
    if create_shortcut():
        print("🎉 Raccourci créé avec succès sur le bureau!")
    else:
        print("❌ Erreur lors de la création du raccourci")
