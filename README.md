# 🎙️ Live Translation WebServer

Système de traduction en temps réel utilisant Whisper, avec interface web React et support GPU automatique.

## 📦 Prérequis

- Python 3.8+
- Node.js 16+
- Microphone
- (Optionnel) GPU NVIDIA ou Apple Silicon

## 🚀 Installation Rapide

### Option 1: Installation Automatique (Recommandée)

```bash
# Cloner le projet
git clone https://github.com/MisterGoodDeal/live-translation-webserver.git
cd live-translation-webserver

# Installation complète en une commande
python run_all.py
```

### Option 2: Installation Étape par Étape

```bash
# 1. Installer les dépendances Python
python install_python.py

# 2. Build le projet Next.js
python build_nextjs.py

# 3. Démarrer le serveur
python start_server.py
```

### Option 3: Installation Manuelle

```bash
# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# ou
.venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer le support GPU (optionnel)
python install_gpu.py
```

## 🎮 Support GPU Automatique

Le script `install_gpu.py` détecte automatiquement votre machine et installe la bonne version de PyTorch :

- **🍎 Mac M1/M2/M3** : Metal Performance Shaders (MPS)
- **🎮 NVIDIA GPU** : CUDA 11.8
- **💻 CPU** : Version CPU optimisée

## 🏃‍♂️ Utilisation

### Utilisation Quotidienne (Recommandée)

```bash
# Démarrer l'application complète
python start_server.py
```

Cette commande :

- ✅ Vérifie que le build Next.js existe
- ✅ Lance le serveur frontend sur le port 3000
- ✅ Lance le serveur backend sur le port 8000
- ✅ Ouvre automatiquement le navigateur

### URLs d'Accès

- **Interface principale** : http://localhost:3000
- **Interface sous-titres** : http://localhost:3000/captions
- **Backend Socket.IO** : http://localhost:8000

### Scripts Disponibles

| Script              | Description                                     |
| ------------------- | ----------------------------------------------- |
| `install_python.py` | Installe les dépendances Python + GPU           |
| `build_nextjs.py`   | Build le projet Next.js en fichiers statiques   |
| `start_server.py`   | Démarre le serveur complet (frontend + backend) |
| `run_all.py`        | Exécute tous les scripts dans l'ordre           |

## ⚙️ Configuration

### Interface Web

- **Microphone** : Sélectionnez votre microphone
- **Modèle Whisper** : Choisissez entre small/medium/large
- **GPU** : Activez l'accélération GPU
- **Paramètres audio** : Fréquence, durée des chunks, seuil de volume

### Fichier de configuration

La configuration est sauvegardée dans `config.json` :

```json
{
  "model_name": "small",
  "sample_rate": 16000,
  "chunk_duration": 2,
  "volume_threshold": 0.01,
  "selected_microphone_id": null,
  "use_gpu": false
}
```

## 🔧 Fonctionnalités

- ✅ **Transcription en temps réel** (français → anglais)
- ✅ **Interface web moderne** (React + TypeScript)
- ✅ **Support GPU automatique** (CUDA/Metal/CPU)
- ✅ **Configuration persistante** (localStorage + config.json)
- ✅ **Logs en temps réel**
- ✅ **Sélection de microphone**
- ✅ **Paramètres audio ajustables**
- ✅ **Compatible OBS** (Browser Source)
- ✅ **Scripts d'installation automatisés**
- ✅ **Interface sous-titres dédiée**

## 📋 Prérequis

- Python 3.8+
- Node.js 16+
- Microphone
- (Optionnel) GPU NVIDIA ou Apple Silicon

## 🐛 Dépannage

### Problème de microphone

```bash
# Lister les microphones disponibles
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Problème GPU

```bash
# Vérifier l'installation PyTorch
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'MPS: {torch.backends.mps.is_available() if hasattr(torch.backends, \"mps\") else False}')"
```

### Réinstaller PyTorch GPU

```bash
python install_gpu.py
```

## 📁 Structure du Projet

```
live-translation-webserver/
├── main.py                    # Serveur Python principal
├── install_python.py          # Installation dépendances Python
├── build_nextjs.py            # Build projet Next.js
├── start_server.py            # Démarrage serveur complet
├── run_all.py                 # Script d'installation complète
├── install_gpu.py             # Script d'installation GPU
├── requirements.txt           # Dépendances Python
├── config.json               # Configuration persistante
└── live-translation-front/
    ├── pages/
    │   ├── index.tsx         # Interface principale
    │   └── captions/
    │       └── index.tsx     # Interface sous-titres
    ├── contexts/
    │   └── socket.contexts.tsx
    └── out/                  # Build Next.js (généré)
```

## 🎯 Utilisation avec OBS

### Interface Principale

1. URL: `http://localhost:3000`
2. Paramétrez l'interface comme vous le souhaitez
3. Activez la transcription depuis l'interface

### Interface Sous-titres (Recommandée)

1. Ajoutez une source "Browser Source"
2. URL: `http://localhost:3000/captions`
3. Mettre un CSS custom pour la source

```css
:root {
  background-color: transparent;
}
```

4. Fond transparent activé

## 📝 Notes

- Le modèle Whisper est téléchargé automatiquement au premier lancement
- Les modèles plus gros (medium/large) sont plus précis mais plus lents
- L'activation GPU nécessite un redémarrage du serveur
- La configuration est sauvegardée automatiquement (localStorage + config.json)
- Compatible Mac, Windows et Linux
- Les scripts gèrent automatiquement l'installation et le build
