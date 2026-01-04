import React from 'react';

const MetricBox = ({ label, value, subtext }) => (
    <div className="bg-surface/40 p-3 rounded-lg border border-white/5 flex flex-col items-center justify-center text-center">
        <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-gray-400">
            {value}
        </span>
        <span className="text-xs text-secondary mt-1 uppercase tracking-wide">{label}</span>
        {subtext && <span className="text-[10px] text-gray-500 mt-0.5">{subtext}</span>}
    </div>
);

const formatNumber = (num, decimals = 1) => {
    if (num >= 1000000) return (num / 1000000).toFixed(decimals) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(decimals) + 'K';
    return num.toString();
};

export function VllmStatus({ data }) {
    const server = data?.vllm?.server || {};
    const metrics = data?.vllm?.metrics || {};

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Status Card */}
            <div className="glass-card p-6 flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -z-10"></div>

                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-lg font-semibold text-white mb-1">vLLM Server</h2>
                        <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${server.connected ? 'bg-success animate-pulse' : 'bg-danger'}`}></span>
                            <span className={server.connected ? 'text-success' : 'text-danger'}>
                                {server.connected ? 'Running' : 'Disconnected'}
                            </span>
                        </div>
                    </div>
                    <div className="p-2 bg-white/5 rounded-lg">
                        <svg className="w-6 h-6 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 12H18L15 21L9 3L6 12H2"></path>
                        </svg>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-sm text-gray-400">URL</span>
                        <span className="text-sm font-mono text-primary truncate max-w-[200px]">{server.url || '--'}</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-sm text-gray-400">Version</span>
                        <span className="text-sm font-mono text-white">{server.version || '--'}</span>
                    </div>
                    <div className="flex justify-between items-center py-2">
                        <span className="text-sm text-gray-400">Loaded Models</span>
                        <span className="text-white font-medium bg-white/10 px-2 py-0.5 rounded text-sm">
                            {server.models_loaded || '0'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Metrics Card */}
            <div className="lg:col-span-2 glass-card p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-accent/10 rounded-lg text-accent">
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="20" x2="18" y2="10"></line>
                            <line x1="12" y1="20" x2="12" y2="4"></line>
                            <line x1="6" y1="20" x2="6" y2="14"></line>
                        </svg>
                    </div>
                    <h2 className="text-lg font-semibold text-white">Performance Metrics</h2>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricBox
                        label="Total Requests"
                        value={formatNumber(metrics.requests_total || 0)}
                    />
                    <MetricBox
                        label="Running Req"
                        value={metrics.requests_running || 0}
                        subtext="Active"
                    />
                    <MetricBox
                        label="Tokens"
                        value={formatNumber(metrics.tokens_generated || 0)}
                        subtext="Generated"
                    />
                    <MetricBox
                        label="Throughput"
                        value={(metrics.throughput_tokens_per_sec || 0).toFixed(1)}
                        subtext="Tokens/sec"
                    />
                </div>
            </div>
        </div>
    );
}
