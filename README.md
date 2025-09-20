# 🎙️ Live Translation WebServer

Real-time translation system using Whisper, with React web interface and automatic GPU support.

## 📦 Prerequisites

- Python 3.8+
- Node.js 16+
- Microphone
- (Optional) NVIDIA GPU or Apple Silicon

## 🚀 Quick Installation

### Option 1: Automatic Installation (Recommended)

```bash
# Clone the project
git clone https://github.com/MisterGoodDeal/live-translation-webserver.git
cd live-translation-webserver

# Complete installation in one command
python run_all.py
```

### Option 2: Step-by-Step Installation

```bash
# 1. Install Python dependencies
python install_python.py

# 2. Build the Next.js project
python build_nextjs.py

# 3. Start the server
python start_server.py
```

### Option 3: Manual Installation

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure GPU support (optional)
python install_gpu.py
```

## 🎮 Automatic GPU Support

The `install_gpu.py` script automatically detects your machine and installs the correct PyTorch version:

- **🍎 Mac M1/M2/M3** : Metal Performance Shaders (MPS)
- **🎮 NVIDIA GPU** : CUDA 11.8
- **💻 CPU** : Optimized CPU version

## 🏃‍♂️ Usage

### Daily Usage (Recommended)

```bash
# Start the complete application
python start_server.py
```

This command:

- ✅ Verifies that the Next.js build exists
- ✅ Launches the frontend server on port 3000
- ✅ Launches the backend server on port 8000
- ✅ Automatically opens the browser

### Access URLs

- **Main Interface** : http://localhost:3000
- **Captions Interface** : http://localhost:3000/captions
- **Backend Socket.IO** : http://localhost:8000

### Available Scripts

| Script              | Description                                     |
| ------------------- | ----------------------------------------------- |
| `install_python.py` | Installs Python dependencies + GPU              |
| `build_nextjs.py`   | Builds the Next.js project into static files    |
| `start_server.py`   | Starts the complete server (frontend + backend) |
| `run_all.py`        | Runs all scripts in order                       |

## ⚙️ Configuration

### Web Interface

- **Microphone** : Select your microphone
- **Whisper Model** : Choose between small/medium/large
- **GPU** : Enable GPU acceleration
- **Audio Parameters** : Frequency, chunk duration, volume threshold

### Configuration File

The configuration is saved in `config.json`:

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

## 🔧 Features

- ✅ **Real-time transcription** (French → English)
- ✅ **Modern web interface** (React + TypeScript)
- ✅ **Automatic GPU support** (CUDA/Metal/CPU)
- ✅ **Persistent configuration** (localStorage + config.json)
- ✅ **Real-time logs**
- ✅ **Microphone selection**
- ✅ **Adjustable audio parameters**
- ✅ **OBS compatible** (Browser Source)
- ✅ **Automated installation scripts**
- ✅ **Dedicated captions interface**

## 🐛 Troubleshooting

### Microphone Issues

```bash
# List available microphones
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### GPU Issues

```bash
# Check PyTorch installation
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'MPS: {torch.backends.mps.is_available() if hasattr(torch.backends, \"mps\") else False}')"
```

### Reinstall PyTorch GPU

```bash
python install_gpu.py
```

## 📁 Project Structure

```
live-translation-webserver/
├── main.py                    # Main Python server
├── install_python.py          # Python dependencies installation
├── build_nextjs.py            # Next.js project build
├── start_server.py            # Complete server startup
├── run_all.py                 # Complete installation script
├── install_gpu.py             # GPU installation script
├── requirements.txt           # Python dependencies
├── config.json               # Persistent configuration
└── live-translation-front/
    ├── pages/
    │   ├── index.tsx         # Main interface
    │   └── captions/
    │       └── index.tsx     # Captions interface
    ├── contexts/
    │   └── socket.contexts.tsx
    └── out/                  # Next.js build (generated)
```

## 🎯 Usage with OBS

### Main Interface

1. URL: `http://localhost:3000`
2. Configure the interface as desired
3. Activate transcription from the interface

### Captions Interface (Recommended)

1. Add a "Browser Source"
2. URL: `http://localhost:3000/captions`
3. Add custom CSS for the source

```css
:root {
  background-color: transparent;
}
```

4. Enable transparent background

## 📝 Notes

- The Whisper model is automatically downloaded on first launch
- Larger models (medium/large) are more accurate but slower
- GPU activation requires a server restart
- Configuration is automatically saved (localStorage + config.json)
- Compatible with Mac, Windows and Linux
- Scripts automatically handle installation and build
