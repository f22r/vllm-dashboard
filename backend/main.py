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
import re

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

    async def start_server(self, model_name: str, options: dict = None):
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

        # Allow optional port override via options (useful for testing/custom deploy)
        options = options or {}
        requested_port = options.get('port')
        if requested_port is not None:
            try:
                port = int(requested_port)
            except Exception:
                return {"status": "error", "message": f"Invalid port: {requested_port}"}
            # check port availability
            if self._is_port_in_use(port):
                return {"status": "error", "message": f"Port {port} is already in use"}
        else:
            port = self._get_next_free_port()

        try:
            # Command to run vLLM
            cmd = [
                self.vllm_path, "serve", model_name,
                "--port", str(port),
                "--trust-remote-code"
            ]

            # Allow overriding these options from API request (options already set above)
            def add_option(flag, value):
                if value is None:
                    return
                if isinstance(value, bool):
                    if value:
                        cmd.append(flag)
                else:
                    cmd.extend([flag, str(value)])

            # Determine served model name (alias) to pass to vLLM and store for routing
            served_name_option = options.get("served_model_name", "vllm-model")
            add_option("--served-model-name", served_name_option)
            # Pass a sensible default max_model_len unless user overrides it.
            # Using 16384 reduces the chance of exceeding derived model limits
            # while still allowing longer contexts for capable models.
            add_option("--max-model-len", options.get("max_model_len", "16384"))
            add_option("--gpu-memory-utilization", options.get("gpu_memory_utilization", "0.90"))
            add_option("--tool-call-parser", options.get("tool_call_parser", "qwen3_xml"))
            add_option("--dtype", options.get("dtype", None))
            add_option("--enforce-eager", options.get("enforce_eager", True))
            add_option("--enable-auto-tool-choice", options.get("enable_auto_tool_choice", True))

            # Additional passthrough options requested by UI
            add_option("--max-num-seqs", options.get("max_num_seqs"))
            add_option("--tensor-parallel-size", options.get("tensor_parallel_size"))
            add_option("--mamba_ssm_cache_dtype", options.get("mamba_ssm_cache_dtype"))
            add_option("--reasoning-parser-plugin", options.get("reasoning_parser_plugin"))
            add_option("--reasoning-parser", options.get("reasoning_parser"))
            add_option("--kv-cache-dtype", options.get("kv_cache_dtype"))

            # Networking and batching related options
            add_option("--host", options.get("host"))
            # swap-space can be used to configure host swap for big models
            add_option("--swap-space", options.get("swap_space"))
            add_option("--max-num-batched-tokens", options.get("max_num_batched_tokens"))
            # NOTE: do not inject unsupported CLI flags here. If a model needs a
            # different internal kernel layout, it should be handled by vLLM's
            # own configuration or model code. We previously attempted to add
            # `--head-first` for Qwen models, but that flag is not recognized
            # by the `vllm` CLI and causes startup errors.
            # Additional optional arguments (pass-through)
            extra_args = options.get("extra_args")
            if extra_args and isinstance(extra_args, list):
                cmd.extend(extra_args)

            # Fix for models without chat template (like OPT)
            # Transformers v4.44+ requires explicit template
            # if "opt" in model_name.lower() or "pythia" in model_name.lower() or "gpt" in model_name.lower():
            #      template_path = os.path.join(os.path.dirname(__file__), "chat_template.jinja")
            #      cmd.extend(["--chat-template", template_path])
            
            print(f"Starting vLLM [{model_name}] on port {port}: {' '.join(cmd)}")

            # Ensure the child vLLM process has the HF token in its environment
            # so it can download gated models without unauthenticated warnings.
            proc_env = os.environ.copy()
            hf_token = os.getenv("HF_TOKEN")
            if hf_token:
                proc_env["HF_TOKEN"] = hf_token
                proc_env["HUGGINGFACE_HUB_TOKEN"] = hf_token

            # De-duplicate flags to avoid passing the same option twice
            # (e.g. when `extra_args` includes a flag already added above).
            deduped_cmd = []
            seen_flags = set()
            i = 0
            while i < len(cmd):
                part = cmd[i]
                if part.startswith("--"):
                    flag = part
                    # If we've already seen this flag, skip it and its value (if any)
                    if flag in seen_flags:
                        # skip flag
                        i += 1
                        # skip following value if it's not another flag
                        if i < len(cmd) and not cmd[i].startswith("--"):
                            i += 1
                        continue
                    seen_flags.add(flag)
                    deduped_cmd.append(flag)
                    # if there's a value token following, include it
                    if i + 1 < len(cmd) and not cmd[i + 1].startswith("--"):
                        deduped_cmd.append(cmd[i + 1])
                        i += 2
                        continue
                    i += 1
                else:
                    # positional or program path
                    deduped_cmd.append(part)
                    i += 1

            process = await asyncio.create_subprocess_exec(
                *deduped_cmd,
                env=proc_env
            )
            
            # Normalize served model name to a simple string for routing
            served_name = None
            if served_name_option is not None:
                if isinstance(served_name_option, (list, tuple)) and len(served_name_option) > 0:
                    served_name = str(served_name_option[0])
                else:
                    served_name = str(served_name_option)

            self.processes[model_name] = {
                'process': process,
                'port': port,
                'status': 'starting',
                'served_model_name': served_name
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
    options = config.get("options", {})
    return await vllm_manager.start_server(model, options)

@app.post("/api/vllm/stop")
async def stop_vllm(config: dict = None):
    # Support stopping specific model. Accept either the internal process key or the
    # served_model_name alias provided when the model was started.
    model = config.get("model") if config else None

    if model:
        # If exact key exists, stop it
        if model in vllm_manager.processes:
            return await vllm_manager.stop_server(model)

        # Otherwise, try to find by served_model_name alias
        for key, info in list(vllm_manager.processes.items()):
            served = info.get('served_model_name')
            if served and str(served) == str(model):
                return await vllm_manager.stop_server(key)

        # Not found
        return {"status": "error", "message": f"Model {model} not found"}

    # No model specified -> stop all
    return await vllm_manager.stop_server(None)

@app.get("/api/vllm/control/status")
async def get_control_status():
    return vllm_manager.get_status()

@app.post("/api/vllm/chat")
async def chat_completion(request: dict):
    model_name = request.get("model")
    messages = request.get("messages", [])
    
    if not model_name:
        return {"error": "Model name is required"}
    
    # 1. Find the port and served_model_name for the running model
    target_port = None
    target_model_key = None
    target_served_name = None

    # Try exact match against process key
    if model_name in vllm_manager.processes:
        target_port = vllm_manager.processes[model_name]['port']
        target_model_key = model_name
        target_served_name = vllm_manager.processes[model_name].get('served_model_name')
    else:
        # Try matching against served_model_name alias first
        for name, info in vllm_manager.processes.items():
            served = info.get('served_model_name')
            if served and model_name == served:
                target_port = info['port']
                target_model_key = name
                target_served_name = served
                break

        # Fallback: fuzzy match against stored process keys
        if target_port is None:
            for name, info in vllm_manager.processes.items():
                if model_name in name:
                    target_port = info['port']
                    target_model_key = name
                    target_served_name = info.get('served_model_name')
                    break
    
    if not target_port:
        return {"error": f"Model {model_name} is not currently running"}
    
    # 2. Forward request to VLLM — use served_model_name alias if available, otherwise use original
    vllm_api_url = f"http://localhost:{target_port}/v1/chat/completions"

    model_to_send = target_served_name or model_name

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                vllm_api_url,
                json={
                    "model": model_to_send,
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            # Sanitize response to remove internal reasoning tags (e.g., <think>...</think>)
            try:
                resp_json = response.json()
            except Exception:
                return {"error": "Invalid response from vLLM"}

            # Clean message content in choices (OpenAI-like responses)
            if isinstance(resp_json, dict) and resp_json.get("choices"):
                for choice in resp_json.get("choices", []):
                    # choice may have OpenAI-style message content
                    message = choice.get("message") if isinstance(choice, dict) else None
                    if isinstance(message, dict):
                        content = message.get("content", "")
                        if isinstance(content, str) and content:
                            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
                            message["content"] = content.strip()
                    # fallback: plain text field
                    if isinstance(choice, dict) and isinstance(choice.get("text"), str):
                        text = choice.get("text", "")
                        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
                        choice["text"] = text.strip()

            return resp_json
    except Exception as e:
        return {"error": f"Failed to communicate with vLLM on port {target_port}: {str(e)}"}

# Global state for downloads
active_downloads = {} # { model_name: { 'status': 'downloading|done|error', 'progress': '...', 'log': '...' } }

async def run_download_script(model_name: str, token: str = None):
    """Run download in a subprocess and capture output."""
    active_downloads[model_name] = {'status': 'downloading', 'progress': 'Starting...', 'log': ''}
    
    try:
        # Ensure huggingface_hub is available; provide clearer error if missing
        try:
            import huggingface_hub
        except ModuleNotFoundError:
            msg = "huggingface_hub is not installed. Please run: pip install -r backend/requirements.txt"
            print(f"[Download {model_name}] {msg}")
            active_downloads[model_name] = {'status': 'error', 'progress': msg, 'log': msg}
            return
        # Prepare environment and include HF token from env if not provided
        env = os.environ.copy()
        hf_token = token or os.getenv("HF_TOKEN")
        if hf_token:
            # Common env var names recognized by huggingface libraries
            env["HF_TOKEN"] = hf_token
            env["HUGGINGFACE_HUB_TOKEN"] = hf_token
            env["HUGGING_FACE_HUB_TOKEN"] = hf_token

        # Use python -c to run snapshot_download. Pass the token via environment
        # to avoid shell-quoting issues and keep secrets out of the command string.
        cmd = [
            sys.executable,
            "-c",
            (
                "import os\n"
                "from huggingface_hub import snapshot_download\n"
                "print('Starting download...')\n"
                f"snapshot_download(repo_id='{model_name}', token=os.environ.get('HUGGINGFACE_HUB_TOKEN'))"
            )
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

@app.post("/api/vllm/download/clear")
async def clear_download_status(request: dict = None):
    """Clear finished or failed download logs."""
    model_name = request.get("model") if request else None
    
    if model_name:
        if model_name in active_downloads:
            # Only allow clearing if not currently downloading
            if active_downloads[model_name]['status'] == 'downloading':
                 return {"status": "error", "message": "Cannot clear active download"}
            del active_downloads[model_name]
    else:
        # Clear all non-active
        to_remove = [k for k, v in active_downloads.items() if v['status'] != 'downloading']
        for k in to_remove:
            del active_downloads[k]
            
    return {"status": "success", "message": "Download logs cleared"}

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

@app.delete("/api/vllm/models/{model_path:path}")
async def delete_model(model_path: str):
    """Delete a model from HuggingFace cache."""
    import shutil
    
    # Check if model is currently running
    if model_path in vllm_manager.processes:
        return {"status": "error", "message": f"Cannot delete {model_path}: model is currently running. Stop it first."}
    
    # Convert model path to cache directory name
    # e.g., facebook/opt-125m -> models--facebook--opt-125m
    cache_name = "models--" + model_path.replace("/", "--")
    cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub")) / cache_name
    
    if not cache_dir.exists():
        return {"status": "error", "message": f"Model {model_path} not found in cache"}
    
    try:
        shutil.rmtree(cache_dir)
        return {"status": "success", "message": f"Model {model_path} deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete {model_path}: {str(e)}"}


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
        """Get vLLM performance metrics.

        If multiple vLLM instances are managed (multi-model), aggregate metrics
        from each running instance's `/metrics` endpoint so the dashboard shows
        combined totals instead of relying on a single VLLM_URL.
        """
        # Helper to parse Prometheus-style metrics text into numbers we care about
        def parse_metrics_text(text: str):
            metrics = {
                'requests_total': 0,
                'requests_running': 0,
                'tokens_generated': 0,
            }
            if not text:
                return metrics
            for line in text.splitlines():
                if not line or line.startswith('#'):
                    continue
                try:
                    if 'vllm:num_requests_running' in line:
                        metrics['requests_running'] += int(float(line.split()[-1]))
                    elif 'vllm:num_requests_total' in line:
                        metrics['requests_total'] += int(float(line.split()[-1]))
                    elif 'vllm:generation_tokens_total' in line:
                        metrics['tokens_generated'] += int(float(line.split()[-1]))
                except Exception:
                    continue
            return metrics

        # If we have multiple managed processes, query each one and aggregate
        aggregated = {'requests_total': 0, 'requests_running': 0, 'tokens_generated': 0}
        # Gather ports from vllm_manager processes
        ports = []
        for info in vllm_manager.processes.values():
            p = info.get('port')
            if isinstance(p, int):
                ports.append(p)

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Query each /metrics endpoint concurrently
            tasks = []
            for port in ports:
                url = f"http://localhost:{port}/metrics"
                tasks.append(client.get(url))

            if tasks:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for resp in responses:
                    if isinstance(resp, Exception):
                        continue
                    try:
                        text = resp.text
                    except Exception:
                        text = ''
                    parsed = parse_metrics_text(text)
                    aggregated['requests_total'] += parsed['requests_total']
                    aggregated['requests_running'] += parsed['requests_running']
                    aggregated['tokens_generated'] += parsed['tokens_generated']
                return aggregated

        # Fallback: query the configured VLLM_URL (legacy single-server mode)
        vllm = get_vllm_service(VLLM_URL)
        return await vllm.get_metrics()


@app.get("/api/vllm/logs")
async def get_vllm_logs(lines: int = 200):
    """Return latest backend self logs from pm2."""
    try:
        import subprocess
        result = subprocess.run(
            ["pm2", "logs", "vllm-backend", "--lines", str(lines), "--nostream", "--no-color"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return {"status": "error", "message": "Failed to fetch pm2 logs", "details": result.stderr}

        # Filter and clean pm2/pm2-logctl header lines, UI polling requests, and empty lines
        import re
        stdout = result.stdout or ""
        filtered_lines = []
        for l in stdout.splitlines():
            if not l or not l.strip():
                continue
            # Remove pm2 tailing header lines
            if l.startswith('[TAILING]'):
                continue
            # Remove the "<path> last N lines:" header pm2 prints
            if re.match(r'^/.*last \d+ lines:?', l):
                continue
            # Skip frontend's own polling requests
            if '/api/vllm/logs' in l:
                continue

            # Remove the pm2 prefix like "0|vllm-bac | " to make logs cleaner
            cleaned_line = re.sub(r'^\d+\|[^|]+\s\|\s', '', l)
            filtered_lines.append(cleaned_line)

        cleaned = "\n".join(filtered_lines)
        return {"status": "success", "logs": cleaned}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
        reload=True,
        access_log=False,
        log_level="info"
    )
