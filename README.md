# 🎙️ Live Translation WebServer

Système de traduction en temps réel utilisant Whisper, avec interface web React et support GPU automatique.

## 🚀 Installation Rapide

### Option 1: Installation Automatique (Recommandée)

```bash
# Cloner le projet
git clone <votre-repo>
cd live-translation-webserver

# Installation automatique complète
python install.py
```

### Option 2: Installation Manuelle

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

### 1. Démarrer le serveur

```bash
python main.py
```

### 2. Démarrer le frontend

```bash
cd live-translation-front
npm install
npm run dev
```

### 3. Ouvrir l'interface

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

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
- ✅ **Configuration persistante**
- ✅ **Logs en temps réel**
- ✅ **Sélection de microphone**
- ✅ **Paramètres audio ajustables**
- ✅ **Compatible OBS** (Browser Source)

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
├── main.py                 # Serveur Python principal
├── install.py             # Script d'installation automatique
├── install_gpu.py         # Script d'installation GPU
├── requirements.txt       # Dépendances Python
├── config.json           # Configuration persistante
└── live-translation-front/
    ├── pages/
    │   └── index.tsx      # Interface principale
    ├── contexts/
    │   └── socket.contexts.tsx
    └── ...
```

## 🎯 Utilisation avec OBS

1. Ajoutez une source "Browser Source"
2. URL: `http://localhost:3000`
3. Largeur: 1920, Hauteur: 1080
4. Activez la transcription depuis l'interface

## 📝 Notes

- Le modèle Whisper est téléchargé automatiquement au premier lancement
- Les modèles plus gros (medium/large) sont plus précis mais plus lents
- L'activation GPU nécessite un redémarrage du serveur
- Compatible Mac, Windows et Linux
