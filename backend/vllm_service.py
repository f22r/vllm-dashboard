"""
vLLM Integration Service
Handles communication with vLLM server for model management and metrics.
"""

import httpx
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class VLLMServerInfo:
    connected: bool
    url: str
    status: str
    version: str = "unknown"
    models_loaded: int = 0


@dataclass
class VLLMMetrics:
    requests_total: int = 0
    requests_running: int = 0
    tokens_generated: int = 0
    avg_latency_ms: float = 0.0
    throughput_tokens_per_sec: float = 0.0


class VLLMService:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_server_info(self) -> dict:
        """Get vLLM server status and info."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                # Try to get version info
                version = "unknown"
                try:
                    version_resp = await self.client.get(f"{self.base_url}/version")
                    if version_resp.status_code == 200:
                        version = version_resp.json().get("version", "unknown")
                except Exception:
                    pass
                
                info = VLLMServerInfo(
                    connected=True,
                    url=self.base_url,
                    status="running",
                    version=version
                )
                return asdict(info)
            else:
                return asdict(VLLMServerInfo(
                    connected=False,
                    url=self.base_url,
                    status=f"error: {response.status_code}"
                ))
        except Exception as e:
            return asdict(VLLMServerInfo(
                connected=False,
                url=self.base_url,
                status=f"disconnected: {str(e)[:50]}"
            ))
    
    async def get_models(self) -> list[dict]:
        """Get list of available models."""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                return [
                    {
                        "id": m.get("id", "unknown"),
                        "object": m.get("object", "model"),
                        "owned_by": m.get("owned_by", "vllm"),
                        "created": m.get("created", 0)
                    }
                    for m in models
                ]
            return []
        except Exception:
            return []
    
    async def get_metrics(self) -> dict:
        """Get vLLM performance metrics."""
        try:
            response = await self.client.get(f"{self.base_url}/metrics")
            if response.status_code == 200:
                # Parse Prometheus-style metrics
                text = response.text
                metrics = VLLMMetrics()
                
                for line in text.split("\n"):
                    if line.startswith("#") or not line.strip():
                        continue
                    
                    if "vllm:num_requests_running" in line:
                        try:
                            metrics.requests_running = int(float(line.split()[-1]))
                        except ValueError:
                            pass
                    elif "vllm:num_requests_total" in line:
                        try:
                            metrics.requests_total = int(float(line.split()[-1]))
                        except ValueError:
                            pass
                    elif "vllm:generation_tokens_total" in line:
                        try:
                            metrics.tokens_generated = int(float(line.split()[-1]))
                        except ValueError:
                            pass
                
                return asdict(metrics)
            return asdict(VLLMMetrics())
        except Exception:
            return asdict(VLLMMetrics())
    
    async def chat_completions(
        self,
        messages: list[dict],
        model: str = "default",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Optional[dict]:
        """Send chat completion request to vLLM."""
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_vllm_service: Optional[VLLMService] = None


def get_vllm_service(base_url: str = "http://localhost:8001") -> VLLMService:
    """Get or create vLLM service instance."""
    global _vllm_service
    if _vllm_service is None:
        _vllm_service = VLLMService(base_url)
    return _vllm_service
