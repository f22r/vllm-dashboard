import React, { useState, useEffect } from 'react';

const availableModelsMock = [
    // This will be populated by API
];

export function ModelManager({ data }) {
    return (
        <div className="w-full max-w-7xl mx-auto pb-10">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">Model Management</h1>
                <p className="text-gray-400">Deploy, manage, and download LLM models</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-8">
                    <ActiveModelControl gpuStats={data?.system?.gpu} />
                    <ModelFilesList />
                </div>
                <div>
                    <DownloadModelCard downloads={data?.downloads} />
                </div>
            </div>
        </div>
    );
}

function ActiveModelControl({ gpuStats }) {
    const [runningModels, setRunningModels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedModel, setSelectedModel] = useState('');
    const [customModel, setCustomModel] = useState('facebook/opt-125m');
    const [availableModels, setAvailableModels] = useState([]);

    useEffect(() => {
        fetchAvailableModels();
        updateControlStatus();
        const interval = setInterval(updateControlStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchAvailableModels = async () => {
        try {
            const response = await fetch('/api/vllm/available-models');
            const models = await response.json();
            setAvailableModels(models);
        } catch (error) {
            console.error('Failed to fetch available models:', error);
        }
    };

    const updateControlStatus = async () => {
        try {
            const response = await fetch('/api/vllm/control/status');
            const data = await response.json();
            if (data.models) {
                setRunningModels(data.models);
            } else {
                setRunningModels([]);
            }
        } catch (error) {
            console.error('Failed to get status:', error);
        }
    };

    const handleStart = async () => {
        const modelToLaunch = customModel.trim();
        if (!modelToLaunch) return;

        if (runningModels.some(m => m.name === modelToLaunch)) {
            alert('Model is already running!');
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/api/vllm/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelToLaunch })
            });
            const data = await response.json();
            if (data.status === 'success') {
                setTimeout(updateControlStatus, 2000);
            } else {
                alert(`Error: ${data.message}`);
                updateControlStatus();
            }
        } catch (error) {
            alert('Failed to send start command');
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async (modelName) => {
        setLoading(true);
        try {
            const response = await fetch('/api/vllm/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelName }) // If modelName is null, backend stops all/current
            });
            const data = await response.json();
            if (data.status === 'success') {
                if (modelName) {
                    setRunningModels(prev => prev.filter(m => m.name !== modelName));
                } else {
                    setRunningModels([]);
                }
                setTimeout(updateControlStatus, 1000);
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            alert('Failed to send stop command');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-card p-6">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <svg className="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
                Deploy Model
            </h2>

            {/* Active Models List */}
            <div className="mb-8 space-y-3">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wide">Active Models</h3>
                    <div className="flex gap-3">
                        {gpuStats && (
                            <div className="text-xs bg-white/10 px-2 py-0.5 rounded text-gray-300 flex items-center gap-2">
                                <span className={gpuStats.memory_percent > 80 ? "text-red-400" : "text-primary"}>
                                    VRAM: {gpuStats.memory_used_gb} / {gpuStats.memory_total_gb} GB ({gpuStats.memory_percent}%)
                                </span>
                            </div>
                        )}
                        <span className="text-xs bg-white/10 px-2 py-0.5 rounded text-gray-300">{runningModels.length} Running</span>
                    </div>
                </div>

                {runningModels.length === 0 ? (
                    <div className="text-center py-6 border border-white/5 rounded-xl bg-white/5 text-gray-500 text-sm">
                        No models currently running.
                    </div>
                ) : (
                    runningModels.map((model) => (
                        <div key={model.name} className="flex items-center justify-between p-4 bg-surface/50 border border-white/10 rounded-xl group hover:border-white/20 transition-colors">
                            <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${model.status === 'running' ? 'bg-success animate-pulse' : 'bg-warning animate-pulse'}`}></div>
                                <div>
                                    <div className="font-mono text-white text-sm">{model.name}</div>
                                    <div className="text-xs text-gray-400">Port: <span className="text-primary">{model.port}</span> • Status: <span className="uppercase">{model.status}</span></div>
                                </div>
                            </div>
                            <button
                                onClick={() => handleStop(model.name)}
                                className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-bold rounded-lg border border-red-500/20 transition-colors"
                            >
                                STOP
                            </button>
                        </div>
                    ))
                )}
            </div>

            <div className="space-y-4 pt-4 border-t border-white/5">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wide mb-2">Launch New</h3>
                <div>
                    <label className="block text-sm text-gray-400 mb-2">Select Cached Model</label>
                    <select
                        className="w-full bg-background border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary transition-colors"
                        onChange={(e) => {
                            setSelectedModel(e.target.value);
                            if (e.target.value) setCustomModel(e.target.value);
                        }}
                        value={selectedModel}
                    >
                        <option value="">-- Choose from Cache --</option>
                        {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                </div>

                <div className="flex gap-4 pt-2">
                    <button
                        onClick={handleStart}
                        disabled={loading}
                        className="flex-1 bg-primary hover:bg-blue-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-all flex items-center justify-center gap-2"
                    >
                        {loading ? (
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        ) : (
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
                        )}
                        Launch
                    </button>

                    {runningModels.length > 0 && (
                        <button
                            onClick={() => handleStop(null)}
                            title="Kill all running models"
                            disabled={loading}
                            className="bg-red-500/10 hover:bg-red-500/20 text-red-500 hover:text-red-400 border border-red-500/20 font-bold px-6 py-3 rounded-lg transition-all flex items-center justify-center gap-2"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

function DownloadModelCard({ downloads }) {
    const [modelName, setModelName] = useState('');
    const [isDownloading, setIsDownloading] = useState(false);

    // Check if current model is being downloaded
    const currentDownload = downloads?.[modelName] || Object.values(downloads || {}).find(d => d.status === 'downloading');

    const handleDownload = async () => {
        if (!modelName) return;
        setIsDownloading(true);
        try {
            const response = await fetch('/api/vllm/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelName })
            });
            const data = await response.json();
            if (data.status === 'success') {
                // Alert handled by UI update
            } else {
                alert(`Error: ${data.message}`);
                setIsDownloading(false);
            }
        } catch (e) {
            alert("Failed to initiate download.");
            setIsDownloading(false);
        }
    };

    // Auto-update local state based on global downloads
    useEffect(() => {
        if (downloads && modelName && downloads[modelName]) {
            setIsDownloading(downloads[modelName].status === 'downloading');
        }
    }, [downloads, modelName]);

    return (
        <div className="glass-card p-6 h-fit bg-gradient-to-br from-surface/50 to-primary/5 border-primary/20">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
                <svg className="w-5 h-5 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
                Download New Model
            </h2>
            <p className="text-sm text-gray-400 mb-6">
                Download models directly from HuggingFace Hub to your local cache.
            </p>

            <div className="space-y-4">
                <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">HuggingFace Repo ID</label>
                    <input
                        type="text"
                        className="w-full bg-background border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent transition-colors text-sm"
                        placeholder="e.g. mistralai/Mistral-7B-v0.1"
                        value={modelName}
                        onChange={(e) => setModelName(e.target.value)}
                    />
                </div>

                <button
                    onClick={handleDownload}
                    disabled={isDownloading || !modelName}
                    className="w-full bg-accent hover:bg-violet-600 disabled:bg-gray-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg transition-all shadow-lg shadow-accent/25 flex items-center justify-center gap-2"
                >
                    {isDownloading ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            Downloading...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
                            Pull Model
                        </>
                    )}
                </button>
            </div>

            {/* Download Progress Display */}
            {downloads && Object.entries(downloads).map(([name, status]) => (
                <div key={name} className="mt-4 p-3 bg-black/40 rounded-lg border border-white/10 text-xs font-mono group relative">
                    <div className="flex justify-between text-gray-400 mb-1 pr-4">
                        <span className="truncate max-w-[70%]">{name}</span>
                        <span className={status.status === 'error' ? 'text-red-400' : status.status === 'done' ? 'text-green-400' : 'text-blue-400'}>
                            {status.status}
                        </span>
                    </div>
                    <div className="text-white truncate" title={status.log}>
                        {status.progress || status.log || 'Initializing...'}
                    </div>

                    {status.status !== 'downloading' && (
                        <button
                            onClick={async (e) => {
                                e.stopPropagation();
                                try {
                                    await fetch('/api/vllm/download/clear', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ model: name })
                                    });
                                } catch (e) { console.error(e); }
                            }}
                            className="absolute top-2 right-2 text-gray-600 hover:text-white transition-colors"
                            title="Clear log"
                        >
                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    )}
                </div>
            ))}


            <div className="mt-6 pt-6 border-t border-white/5">
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Popular Models</h4>
                <div className="flex flex-wrap gap-2">
                    {['facebook/opt-125m', 'mistralai/Mistral-7B-v0.1', 'meta-llama/Llama-2-7b-hf'].map(tag => (
                        <button
                            key={tag}
                            onClick={() => setModelName(tag)}
                            className="bg-white/5 hover:bg-white/10 border border-white/5 rounded px-3 py-1.5 text-xs text-gray-300 transition-colors"
                        >
                            {tag}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

function ModelFilesList() {
    const [models, setModels] = useState([]);
    const [deleting, setDeleting] = useState(null);

    const fetchModels = () => {
        fetch('/api/vllm/available-models')
            .then(res => res.json())
            .then(data => setModels(data))
            .catch(err => console.error(err));
    };

    useEffect(() => {
        fetchModels();
    }, []);

    const handleDelete = async (model) => {
        if (!confirm(`Are you sure you want to delete "${model}"?\n\nThis will permanently remove the model from your local cache.`)) {
            return;
        }

        setDeleting(model);
        try {
            const response = await fetch(`/api/vllm/models/${encodeURIComponent(model)}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.status === 'success') {
                fetchModels(); // Refresh list
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (e) {
            alert('Failed to delete model');
        } finally {
            setDeleting(null);
        }
    };

    return (
        <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 14.66V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h5.34"></path><polygon points="18 2 22 6 12 16 8 16 8 12 18 2"></polygon></svg>
                    Local Cache
                </h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={fetchModels}
                        className="text-gray-500 hover:text-white transition-colors p-1"
                        title="Refresh"
                    >
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                    </button>
                    <span className="bg-white/10 px-2 py-1 rounded text-xs font-mono text-gray-400">{models.length} Models</span>
                </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-white/5">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-gray-400 font-medium uppercase tracking-wider text-xs">
                        <tr>
                            <th className="px-6 py-4">Model Name</th>
                            <th className="px-6 py-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {models.length === 0 ? (
                            <tr>
                                <td colSpan="2" className="px-6 py-8 text-center text-gray-500">
                                    No models found in cache.
                                </td>
                            </tr>
                        ) : (
                            models.map(model => (
                                <tr key={model} className="hover:bg-white/5 transition-colors">
                                    <td className="px-6 py-4 font-mono text-gray-200">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center text-xs font-bold text-gray-300 border border-white/10">
                                                HF
                                            </div>
                                            <span className="truncate max-w-[300px]" title={model}>{model}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-3">
                                            <button
                                                className="text-primary hover:text-white transition-colors text-xs font-bold uppercase tracking-wide"
                                                onClick={() => navigator.clipboard.writeText(model)}
                                            >
                                                Copy
                                            </button>
                                            <button
                                                className="text-red-500/70 hover:text-red-400 transition-colors text-xs font-bold uppercase tracking-wide disabled:opacity-50"
                                                onClick={() => handleDelete(model)}
                                                disabled={deleting === model}
                                            >
                                                {deleting === model ? (
                                                    <span className="flex items-center gap-1">
                                                        <div className="w-3 h-3 border border-red-400/30 border-t-red-400 rounded-full animate-spin"></div>
                                                    </span>
                                                ) : 'Delete'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
