# vLLM Dashboard

Real-time monitoring and management dashboard for vLLM server with system resource visualization, model management, and integrated chat.

![Dashboard Preview](docs/preview.png)

## ✨ Features

### 🖥️ Dashboard & Monitoring
- **Real-time Monitoring** - WebSocket-based live updates every 1.5 seconds.
- **System Resources**:
  - **CPU**: Usage percentage and temperature.
  - **Memory**: RAM utilization.
  - **GPU**: NVIDIA GPU stats including VRAM usage, Total VRAM, Compute utilization, Power, and Temperature.
  - **Disk**: Overall disk usage monitoring.
  - **Network**: Real-time upload/download rates.
- **vLLM Status**: Connection status connection to the backend.

### 📦 Model Management
- **Process Control**: 
  - Start and Stop specific vLLM models.
  - **Zombie Killer**: Detects and terminates orphaned "zombie" vLLM processes.
  - **Kill All**: One-click emergency stop to terminate all model processes.
- **Model Library**: 
  - View available models in your local HuggingFace cache.
  - **Download Manager**: Download new models directly from HuggingFace with progress tracking.
- **Multi-Model Support**: Run different models on different ports (managed automatically).

### 💬 Chat Interface
- **Interactive Chat**: Direct interface to chat with your running vLLM models.
- **Auto-Configuration**: Automatically connects to the specific port of the selected running model.
- **Template Handling**: Includes generic fallback templates for models that don't ship with valid chat templates (e.g., base OPT/Pythia models).

### 🎨 Modern UI
- **Design**: Premium dark theme with glassmorphism aesthetics.
- **Tech**: Built with React (Vite) and generic CSS (PostCSS/Tailwind-ready).

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- NVIDIA GPU (Recommended for vLLM)
- Linux OS

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd vllm-dashboard

# 1. Setup Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup Frontend
cd ../frontend
npm install
```

### Running the Application

You need two terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
# Uses port from .env (default: 5511)
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
# Uses port from .env (default: 5510)
npm run dev
```

Open your browser at **http://localhost:5510**

## 📁 Project Structure

```
vllm-dashboard/
├── backend/
│   ├── main.py           # FastAPI app, WebSocket, & Process Manager
│   ├── monitoring.py     # System stats (psutil, pynvml)
│   ├── vllm_service.py   # vLLM Client integration
│   ├── chat_template.jinja # Fallback Jinja2 template
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx      # Main resource monitor
│   │   │   ├── ModelManager.jsx   # Model start/stop/download
│   │   │   ├── ChatInterface.jsx  # Chat UI
│   │   ├── components/   # Reusable UI components
│   │   ├── App.jsx       # Routing & Layout
│   │   └── main.js       # Entry point
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## ⚙️ Configuration

The application uses environment variables for configuration. You can create a `.env` file in the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_URL` | `http://localhost:8001` | Default vLLM URL |
| `FRONTEND_PORT` | `5510` | Frontend dev server port |
| `BACKEND_PORT` | `5511` | Backend API port |
| `HF_TOKEN` | *None* | Hugging Face Token (Required for gated models) |


## 🔌 API Endpoints

### Process Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vllm/start` | POST | Start a generic model instance |
| `/api/vllm/stop` | POST | Stop a model or all models |
| `/api/vllm/control/status` | GET | Get list of managed processes (running/zombies) |
| `/api/vllm/download` | POST | Trigger a HuggingFace model download |
| `/api/vllm/available-models` | GET | List models in local HF cache |

### Chat & Inference
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vllm/chat` | POST | Proxy chat request to specific model port |

### System Monitoring
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/all` | GET | Complete system stats snapshot |
| `/ws/monitoring` | WebSocket | Real-time stream of System + vLLM + Process data |

## 📄 License

MIT License

---

Made with ❤️ for the Local AI Community
