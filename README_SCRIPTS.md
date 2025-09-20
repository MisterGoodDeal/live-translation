# 🚀 Live Translation - Scripts d'Installation

## Scripts Disponibles

### 1. `install_python.py`

Installe toutes les dépendances Python nécessaires.

```bash
python install_python.py
```

**Fait :**

- ✅ Vérifie la version Python (3.8+)
- ✅ Crée un environnement virtuel `.venv`
- ✅ Installe les dépendances depuis `requirements.txt`
- ✅ Configure le support GPU (CUDA/MPS)

### 2. `build_nextjs.py`

Build le projet Next.js en fichiers statiques.

```bash
python build_nextjs.py
```

**Fait :**

- ✅ Vérifie Node.js et npm
- ✅ Installe les dépendances npm
- ✅ Crée `next.config.js` si nécessaire
- ✅ Build l'application dans `live-translation-front/out/`

### 3. `start_server.py`

Démarre le serveur complet (frontend + backend).

```bash
python start_server.py
```

**Fait :**

- ✅ Vérifie que le build Next.js existe
- ✅ Lance le serveur frontend sur le port 3000
- ✅ Lance le serveur backend sur le port 8000
- ✅ Ouvre automatiquement le navigateur

### 4. `run_all.py` (Optionnel)

Exécute tous les scripts dans l'ordre.

```bash
python run_all.py
```

## 🎯 Utilisation Recommandée

### Première fois :

```bash
python install_python.py
python build_nextjs.py
python start_server.py
```

### Utilisation quotidienne :

```bash
python start_server.py
```

## 📱 URLs

- **Interface principale** : http://localhost:3000
- **Interface sous-titres** : http://localhost:3000/captions
- **Backend Socket.IO** : http://localhost:8000

## 🔧 Dépannage

### Erreur "Build Next.js non trouvé"

```bash
python build_nextjs.py
```

### Erreur "Environnement virtuel non trouvé"

```bash
python install_python.py
```

### Erreur "Node.js non trouvé"

Installez Node.js depuis https://nodejs.org/

## 📁 Structure

```
live-translation-webserver/
├── install_python.py      # Installation Python
├── build_nextjs.py        # Build Next.js
├── start_server.py        # Démarrage serveur
├── run_all.py            # Script complet
├── main.py               # Serveur backend
├── live-translation-front/ # Frontend Next.js
└── .venv/                # Environnement virtuel Python
```
