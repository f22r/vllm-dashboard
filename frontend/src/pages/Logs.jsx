import React, { useEffect, useState } from 'react';

export function Logs() {
    const [logs, setLogs] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lines, setLines] = useState(200);
    const [follow, setFollow] = useState(true);
    const logsRef = React.useRef(null);
    const fetchingRef = React.useRef(false);

    const fetchLogs = async () => {
        // Prevent overlapping fetches
        if (fetchingRef.current) return;
        fetchingRef.current = true;
        setError(null);
        try {
            const res = await fetch(`/api/vllm/logs?lines=${lines}`);
            const data = await res.json();
            if (data.status === 'success') {
                setLogs(data.logs);
                // Ensure view jumps to the latest logs immediately
                setTimeout(() => {
                    if (logsRef.current) {
                        logsRef.current.scrollTop = logsRef.current.scrollHeight;
                    }
                }, 50);
            } else {
                setError(data.message || 'Failed to get logs');
            }
        } catch (e) {
            setError(e.message);
        } finally {
            fetchingRef.current = false;
            setLoading(false);
        }
    };

    useEffect(() => {
        setLoading(true);
        fetchLogs();
    }, [lines]);

    useEffect(() => {
        if (!follow) return;
        // Poll less frequently to reduce load and avoid overlap
        const interval = setInterval(fetchLogs, 5000);
        return () => clearInterval(interval);
    }, [follow, lines]);

    useEffect(() => {
        if (follow && logsRef.current) {
            logsRef.current.scrollTop = logsRef.current.scrollHeight;
        }
    }, [logs, follow]);

    return (
        <div className="w-full max-w-7xl mx-auto pb-10 px-4 md:px-0">
            <header className="mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Backend Logs</h1>
                    <p className="text-gray-400">Tampilkan log proses backend (pm2 vllm-backend).</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <label className="text-xs text-gray-400">Lines:</label>
                    <input
                        type="number"
                        min={10}
                        step={10}
                        value={lines}
                        onChange={(e) => setLines(Number(e.target.value))}
                        className="w-24 bg-background border border-white/10 text-white px-2 py-2 rounded-lg text-sm"
                        aria-label="Log lines"
                    />
                    <button
                        onClick={fetchLogs}
                        className="bg-primary px-4 py-2 rounded-lg font-bold text-white hover:bg-blue-600"
                    >
                        Refresh
                    </button>
                    <button
                        onClick={() => setFollow(!follow)}
                        className={`px-4 py-2 rounded-lg font-bold text-white ${follow ? 'bg-green-500 hover:bg-green-600' : 'bg-gray-700 hover:bg-gray-600'}`}
                    >
                        {follow ? 'Auto-follow ON' : 'Auto-follow OFF'}
                    </button>
                </div>
            </header>

            {error && (
                <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 text-red-200 rounded-lg">{error}</div>
            )}

            <div ref={logsRef} className="h-[65vh] overflow-auto bg-black/40 border border-white/10 rounded-lg p-3 font-mono text-xs text-white whitespace-pre-wrap">
                {logs || 'No logs found'}
            </div>
        </div>
    );
}
