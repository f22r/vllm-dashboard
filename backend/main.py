"""
VLLM Dashboard Backend
FastAPI server with WebSocket support for real-time monitoring.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx

from monitoring import get_all_stats, get_cpu_stats, get_memory_stats, get_gpu_stats
from vllm_service import get_vllm_service


# Configuration
VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8001")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 5111))
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    print("🚀 VLLM Dashboard starting...")
    yield
    # Cleanup
    print("🛑 Shutting down managed vLLM processes...")
    await vllm_manager.stop_server() # Terminates all running models
    
    vllm = get_vllm_service(VLLM_URL)
    await vllm.close()
    print("👋 VLLM Dashboard shutting down...")


app = FastAPI(
    title="VLLM Dashboard API",
    description="Real-time monitoring and management for vLLM",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== vLLM Process Management =====

import psutil

class VLLMManager:
    """Manages multiple vLLM server subprocesses."""
    
    def __init__(self):
        self.processes = {}  # { model_name: {'process': proc, 'port': int, 'status': str} }
        self.vllm_path = "/home/sinergi/AI/vllm/venv/bin/vllm"
        self.base_port = 8001
        self._discover_running_processes()
    
    def _discover_running_processes(self):
        """Discover existing vLLM processes running on the system."""
        print("🔍 Scanning for existing vLLM processes...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
                try:
                    cmdline = proc.info['cmdline']
                    name = proc.info['name']
                    pid = proc.info['pid']
                    
                    # 1. Check for standard "vllm serve" processes
                    cmd_str = ' '.join(cmdline) if cmdline else name
                    if 'vllm' in cmd_str:
                        # Stricter check: 'serve' must be a distinct argument
                        if 'serve' in cmdline:
                            model_name = "Unknown"
                            port = 8001
                            for i, arg in enumerate(cmdline):
                                if arg == 'serve' and i + 1 < len(cmdline):
                                    model_name = cmdline[i+1]
                                if arg == '--port' and i + 1 < len(cmdline):
                                    try: port = int(cmdline[i+1])
                                    except: pass
                            
                            display_name = model_name
                            if model_name == "Unknown":
                                display_name = f"Unknown (PID:{pid})"
                            
                            print(f"✅ Found running vLLM: {display_name} on port {port}")
                            self.processes[display_name] = {
                                'process': proc,
                                'port': port,
                                'status': 'running'
                            }
                            continue

                    # 2. Check for "VLLM::EngineCore" orphans (Zombies)
                    if 'VLLM::EngineCore' in cmd_str or 'VLLM::EngineCore' in name:
                         if proc.info['ppid'] == 1:
                             print(f"💀 Found Zombie vLLM Worker: PID {pid}")
                             self.processes[f"Zombie Process ({pid})"] = {
                                'process': proc,
                                'port': 'N/A',
                                'status': 'zombie'
                            }
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"Error discovering processes: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        except:
            return True

    def _get_next_free_port(self) -> int:
        port = self.base_port
        while self._is_port_in_use(port):
            port += 1
        return port

    async def start_server(self, model_name: str):
        if model_name in self.processes:
             # Check if it's dead
             proc_info = self.processes[model_name]
             if proc_info['process'].returncode is not None:
                 print(f"Cleanup dead process for {model_name}")
                 del self.processes[model_name]
             else:
                 return {"status": "error", "message": f"Model {model_name} is already running on port {proc_info['port']}"}
        
        # Limit max models (simple heuristic based on user VRAM)
        if len(self.processes) >= 3:
             return {"status": "error", "message": "Max model limit reached (3). Stop a model first."}

        port = self._get_next_free_port()
        
        try:
            # Command to run vLLM
            cmd = [
                self.vllm_path, "serve", model_name,
                "--port", str(port),
                "--gpu-memory-utilization", "0.25", # Conservative for multi-model
                "--dtype", "auto",
                "--enforce-eager",
                "--disable-log-stats"
            ]

            # Fix for models without chat template (like OPT)
            # Transformers v4.44+ requires explicit template
            if "opt" in model_name.lower() or "pythia" in model_name.lower() or "gpt" in model_name.lower():
                 template_path = os.path.join(os.path.dirname(__file__), "chat_template.jinja")
                 cmd.extend(["--chat-template", template_path])
            
            print(f"Starting vLLM [{model_name}] on port {port}: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd
                # Inherit stdout/stderr to see logs
            )
            
            self.processes[model_name] = {
                'process': process,
                'port': port,
                'status': 'starting'
            }
            
            return {"status": "success", "message": f"Starting {model_name} on port {port}", "port": port}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def stop_server(self, model_name: str = None):
        if model_name:
            if model_name not in self.processes:
                 return {"status": "error", "message": f"Model {model_name} not found"}
            
            targets = [model_name]
        else:
            targets = list(self.processes.keys())
        
        results = []
        for name in targets:
            proc_info = self.processes.get(name)
            if not proc_info: continue
            
            # Special handling for Zombies
            if "Zombie Process" in name and str(proc_info.get('status')) == 'zombie':
                try:
                    # Extract PID from name "Zombie Process (12345)"
                    import re
                    pid_match = re.search(r'\((\d+)\)', name)
                    if pid_match:
                        pid = int(pid_match.group(1))
                        # Kill it with fire
                        try:
                            os.kill(pid, 9) # SIGKILL
                        except ProcessLookupError:
                            pass # Already dead
                        except Exception as e:
                            print(f"Failed to kill zombie {pid}: {e}")
                            # Fallback to shell
                            import subprocess
                            subprocess.run(f"kill -9 {pid}", shell=True)
                            
                    del self.processes[name]
                    results.append(f"Killed zombie {name}")
                    continue
                except Exception as e:
                    results.append(f"Error killing zombie {name}: {e}")
                    continue

            try:
                proc = proc_info['process']
                port = proc_info['port']
                
                # If it's a real python process object
                if hasattr(proc, 'terminate'):
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                elif isinstance(proc, psutil.Process):
                    # It's a psutil object from discovery
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()

                # Cleanup port just in case
                try:
                    import subprocess
                    pid_port = subprocess.check_output(f"lsof -t -i:{port}", shell=True).decode().strip()
                    if pid_port: subprocess.run(f"kill -9 {pid_port}", shell=True)
                except: pass
                
                del self.processes[name]
                results.append(f"Stopped {name}")
            except Exception as e:
                # Force remove from list if it's dead but threw error
                del self.processes[name]
                results.append(f"Error stopping structure for {name}: {e}")

        return {"status": "success", "message": ", ".join(results)}

    def get_status(self):
        # Update statuses
        active_models = []
        models_to_remove = []
        
        for name, info in self.processes.items():
            proc = info['process']
            is_dead = False
            
            # Check if process is dead based on its type
            if isinstance(proc, psutil.Process):
                try:
                    if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                        # Zombies we want to show, not auto-remove immediately unless we kill them
                        # But for "running check", a zombie is technically not "running" in a useful way
                        # actually, we want to Keep zombies in list so user can kill them
                        pass 
                    else:
                        pass # It is running
                except psutil.NoSuchProcess:
                    is_dead = True
            else:
                # asyncio subprocess
                if proc.returncode is not None:
                    is_dead = True
            
            if is_dead and info['status'] != 'zombie':
                 models_to_remove.append(name)
            else:
                # Check real connectivity to confirm it's "running"
                # Only check if it's NOT a zombie and claims to be starting
                if info['status'] == 'starting' and isinstance(info['port'], int):
                     if self._is_port_in_use(info['port']):
                         info['status'] = 'running'
                
                active_models.append({
                    "name": name,
                    "port": info['port'],
                    "status": info['status']
                })
        
        for name in models_to_remove:
            del self.processes[name]
            
        return {
            "running": len(active_models) > 0,
            "models": active_models
        }

vllm_manager = VLLMManager()

@app.post("/api/vllm/start")
async def start_vllm(config: dict):
    model = config.get("model", "facebook/opt-125m")
    return await vllm_manager.start_server(model)

@app.post("/api/vllm/stop")
async def stop_vllm(config: dict = None):
    # Support stopping specific model
    model = config.get("model") if config else None
    return await vllm_manager.stop_server(model)

@app.get("/api/vllm/control/status")
async def get_control_status():
    return vllm_manager.get_status()

@app.post("/api/vllm/chat")
async def chat_completion(request: dict):
    model_name = request.get("model")
    messages = request.get("messages", [])
    
    if not model_name:
        return {"error": "Model name is required"}
    
    # 1. Find the port for the running model
    target_port = None
    target_model_name = model_name
    
    # Check if we have exact match
    if model_name in vllm_manager.processes:
        target_port = vllm_manager.processes[model_name]['port']
    else:
        # Check if it's an "Unknown" process or by fuzzy match
        for name, info in vllm_manager.processes.items():
            if model_name in name:
                target_port = info['port']
                target_model_name = name # Use the internal name just in case? VLLM cares about the model name in args usually
                break
    
    if not target_port:
        return {"error": f"Model {model_name} is not currently running"}
    
    # 2. Forward request to VLLM
    vllm_api_url = f"http://localhost:{target_port}/v1/chat/completions"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                vllm_api_url,
                json={
                    "model": model_name, # Pass original requested name, as vLLM usually expects the loaded path
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Failed to communicate with vLLM on port {target_port}: {str(e)}"}

# Global state for downloads
active_downloads = {} # { model_name: { 'status': 'downloading|done|error', 'progress': '...', 'log': '...' } }

async def run_download_script(model_name: str, token: str = None):
    """Run download in a subprocess and capture output."""
    active_downloads[model_name] = {'status': 'downloading', 'progress': 'Starting...', 'log': ''}
    
    try:
        # Prepare environment
        env = os.environ.copy()
        if token:
            env["HF_TOKEN"] = token
            env["HUGGING_FACE_HUB_TOKEN"] = token
            
        # Use python -c to run snapshot_download
        cmd = [
            sys.executable, "-c", 
            f"from huggingface_hub import snapshot_download; print('Starting download...'); snapshot_download(repo_id='{model_name}')"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Helper to read stream
        async def read_stream(stream, is_stderr=False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode().strip()
                if not decoded: continue
                
                # Update log
                active_downloads[model_name]['log'] = decoded
                
                # Try to parse progress from stderr (tqdm usually writes to stderr)
                if '%' in decoded:
                     active_downloads[model_name]['progress'] = decoded
                
                print(f"[Download {model_name}] {decoded}")
        
        await asyncio.gather(
            read_stream(process.stdout),
            read_stream(process.stderr, is_stderr=True)
        )
        
        await process.wait()
        
        if process.returncode == 0:
            active_downloads[model_name] = {'status': 'done', 'progress': 'Completed', 'log': 'Finished'}
        else:
            active_downloads[model_name]['status'] = 'error'
            active_downloads[model_name]['progress'] = 'Failed'

    except Exception as e:
        print(f"Download error: {e}")
        active_downloads[model_name] = {'status': 'error', 'progress': str(e), 'log': str(e)}

@app.post("/api/vllm/download")
async def download_model(request: dict, background_tasks: BackgroundTasks):
    model_name = request.get("model")
    token = request.get("token")
    
    if not model_name:
        return {"status": "error", "message": "Model name is required"}
    
    if model_name in active_downloads and active_downloads[model_name]['status'] == 'downloading':
         return {"status": "error", "message": f"Download for {model_name} is already in progress"}
    
    # Start async task
    asyncio.create_task(run_download_script(model_name, token))
    
    return {"status": "success", "message": f"Download initiated for {model_name}"}

@app.get("/api/vllm/available-models")
async def get_available_models():
    """List models found in HuggingFace cache."""
    cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    models = []
    if cache_dir.exists():
        for item in cache_dir.glob("models--*"):
            if item.is_dir():
                # Convert models--facebook--opt-125m to facebook/opt-125m
                name = item.name.replace("models--", "").replace("--", "/")
                models.append(name)
    return models


# ===== REST API Endpoints =====

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/system/all")
async def get_system_stats():
    """Get all system statistics."""
    return get_all_stats()


@app.get("/api/system/cpu")
async def get_cpu():
    """Get CPU statistics."""
    return get_cpu_stats()


@app.get("/api/system/memory")
async def get_memory():
    """Get memory statistics."""
    return get_memory_stats()


@app.get("/api/system/gpu")
async def get_gpu():
    """Get GPU statistics."""
    return get_gpu_stats()


@app.get("/api/vllm/status")
async def get_vllm_status():
    """Get vLLM server status."""
    vllm = get_vllm_service(VLLM_URL)
    return await vllm.get_server_info()


@app.get("/api/vllm/models")
async def get_vllm_models():
    """Get loaded models."""
    vllm = get_vllm_service(VLLM_URL)
    return await vllm.get_models()


@app.get("/api/vllm/metrics")
async def get_vllm_metrics():
    """Get vLLM metrics."""
    vllm = get_vllm_service(VLLM_URL)
    return await vllm.get_metrics()


# ===== WebSocket for Real-time Updates =====

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, data: dict):
        """Send data to all connected clients."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.append(connection)
        
        # Remove dead connections
        for conn in dead_connections:
            self.disconnect(conn)


manager = ConnectionManager()


@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time system monitoring."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Get all stats
            stats = get_all_stats()
            
            # Get vLLM info (legacy connection method - mostly null if multi-model)
            vllm = get_vllm_service(VLLM_URL)
            vllm_info = await vllm.get_server_info()
            vllm_metrics = await vllm.get_metrics()
            
            # Get Multi-model status
            models_status = vllm_manager.get_status().get('models', [])
            
            # Send combined data
            await websocket.send_json({
                "timestamp": datetime.now().isoformat(),
                "system": stats,
                "vllm": {
                    "server": vllm_info,
                    "metrics": vllm_metrics
                },
                "models": models_status,
                "downloads": active_downloads
            })
            
            # Wait before next update
            await asyncio.sleep(1.5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ===== Static File Serving (Production) =====

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        reload=True
    )
