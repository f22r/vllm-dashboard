"""
System Monitoring Module
Provides real-time system metrics for CPU, RAM, GPU, Disk, and Network.
"""

import psutil
from typing import Optional
from dataclasses import dataclass, asdict

# Try to import NVIDIA ML for GPU monitoring
try:
    import pynvml
    pynvml.nvmlInit()
    NVIDIA_AVAILABLE = True
except Exception:
    NVIDIA_AVAILABLE = False


@dataclass
class CPUStats:
    usage_percent: float
    core_count: int
    frequency_mhz: float
    per_core_percent: list[float]
    temperature: Optional[float] = None


@dataclass
class MemoryStats:
    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


@dataclass
class GPUStats:
    available: bool
    name: str = "N/A"
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_percent: float = 0.0
    utilization_percent: float = 0.0
    temperature_c: float = 0.0
    power_watts: float = 0.0


@dataclass
class DiskStats:
    mount_point: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class NetworkStats:
    bytes_sent_mb: float
    bytes_recv_mb: float
    packets_sent: int
    packets_recv: int


def get_cpu_stats() -> dict:
    """Get CPU statistics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    
    # Try to get temperature
    temperature = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    temperature = entries[0].current
                    break
    except Exception:
        pass
    
    stats = CPUStats(
        usage_percent=cpu_percent,
        core_count=psutil.cpu_count(logical=True),
        frequency_mhz=cpu_freq.current if cpu_freq else 0,
        per_core_percent=per_core,
        temperature=temperature
    )
    return asdict(stats)


def get_memory_stats() -> dict:
    """Get memory (RAM) statistics."""
    mem = psutil.virtual_memory()
    stats = MemoryStats(
        total_gb=round(mem.total / (1024**3), 2),
        used_gb=round(mem.used / (1024**3), 2),
        available_gb=round(mem.available / (1024**3), 2),
        percent=mem.percent
    )
    return asdict(stats)


def get_gpu_stats() -> dict:
    """Get GPU statistics (NVIDIA only)."""
    if not NVIDIA_AVAILABLE:
        return asdict(GPUStats(available=False))
    
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except Exception:
            temp = 0
        
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
        except Exception:
            power = 0
        
        stats = GPUStats(
            available=True,
            name=name,
            memory_total_gb=round(mem_info.total / (1024**3), 2),
            memory_used_gb=round(mem_info.used / (1024**3), 2),
            memory_percent=round((mem_info.used / mem_info.total) * 100, 1),
            utilization_percent=utilization.gpu,
            temperature_c=temp,
            power_watts=round(power, 1)
        )
        return asdict(stats)
    except Exception as e:
        return asdict(GPUStats(available=False, name=str(e)))


def get_disk_stats() -> list[dict]:
    """Get disk usage for all partitions."""
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            stats = DiskStats(
                mount_point=partition.mountpoint,
                total_gb=round(usage.total / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                free_gb=round(usage.free / (1024**3), 2),
                percent=usage.percent
            )
            disks.append(asdict(stats))
        except PermissionError:
            continue
    return disks


def get_network_stats() -> dict:
    """Get network I/O statistics."""
    net = psutil.net_io_counters()
    stats = NetworkStats(
        bytes_sent_mb=round(net.bytes_sent / (1024**2), 2),
        bytes_recv_mb=round(net.bytes_recv / (1024**2), 2),
        packets_sent=net.packets_sent,
        packets_recv=net.packets_recv
    )
    return asdict(stats)


def get_all_stats() -> dict:
    """Get all system statistics."""
    return {
        "cpu": get_cpu_stats(),
        "memory": get_memory_stats(),
        "gpu": get_gpu_stats(),
        "disks": get_disk_stats(),
        "network": get_network_stats()
    }
