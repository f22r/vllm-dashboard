import React from 'react';
import { Gauge } from './Gauge';

const Card = ({ title, children, icon }) => (
    <div className="glass-card p-6 flex flex-col items-center relative overflow-hidden group">
        <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider mb-4 w-full flex items-center gap-2">
            {icon && <span className="w-4 h-4">{icon}</span>}
            {title}
        </h3>
        {children}
    </div>
);

const DetailRow = ({ label, value }) => (
    <div className="flex justify-between w-full mt-2 text-sm border-b border-white/5 pb-1 last:border-0 last:pb-0">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-200 font-medium font-mono">{value}</span>
    </div>
);

export function SystemStats({ system }) {
    const cpu = system?.cpu || {};
    const memory = system?.memory || {};
    const gpu = system?.gpu || {};
    const network = system?.network || {};

    const cpuPercent = Math.round(cpu.usage_percent || 0);
    const memoryPercent = Math.round(memory.percent || 0);
    const gpuUtilPercent = Math.round(gpu.utilization_percent || 0);
    const gpuMemPercent = Math.round(gpu.memory_percent || 0);

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card title="CPU Usage" icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                    <rect x="4" y="4" width="16" height="16" rx="2" />
                    <path d="M9 9h6v6H9z" />
                    <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />
                </svg>
            }>
                <div className="mb-4">
                    <Gauge percent={cpuPercent} colorClass="text-primary" />
                </div>
                <div className="w-full space-y-2">
                    <DetailRow label="Cores" value={cpu.core_count || '--'} />
                    <DetailRow label="Frequency" value={`${Math.round(cpu.frequency_mhz || 0)} MHz`} />
                </div>
            </Card>

            <Card title="Memory" icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                    <path d="M6 19v-3h12v3M6 5v3h12V5M6 9h12v6H6z" />
                </svg>
            }>
                <div className="mb-4">
                    <Gauge percent={memoryPercent} colorClass="text-accent" />
                </div>
                <div className="w-full space-y-2">
                    <DetailRow label="Used" value={`${memory.used_gb || 0} GB`} />
                    <DetailRow label="Total" value={`${memory.total_gb || 0} GB`} />
                </div>
            </Card>

            <Card title="GPU" icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <path d="M8 21h8M12 17v4" />
                </svg>
            }>
                <div className="text-xs text-center text-primary mb-2 font-mono truncate w-full px-2">
                    {gpu.available ? (gpu.name || 'Unknown GPU') : 'No GPU'}
                </div>
                <div className="flex gap-2 mb-4">
                    <Gauge percent={gpuUtilPercent} label="Util" size="mini" colorClass="text-purple-400" />
                    <Gauge percent={gpuMemPercent} label="Mem" size="mini" colorClass="text-pink-400" />
                </div>
                <div className="w-full space-y-2">
                    <DetailRow label="VRAM" value={gpu.available ? `${gpu.memory_used_gb || 0} / ${gpu.memory_total_gb || '--'} GB` : '--'} />
                    <DetailRow label="Power" value={gpu.available ? `${gpu.power_watts || 0} W` : '--'} />
                </div>
            </Card>

            <Card title="Network" icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M5 12.55a11 11 0 0 1 14 0M12 2v4M12 20v2" />
                </svg>
            }>
                <div className="flex-1 flex flex-col justify-center w-full space-y-4">
                    <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
                            </div>
                            <span className="text-sm text-gray-400">Sent</span>
                        </div>
                        <span className="font-mono text-white">{network.bytes_sent_mb || 0} MB</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-500/20 rounded-lg text-emerald-400">
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12l7 7 7-7" /></svg>
                            </div>
                            <span className="text-sm text-gray-400">Recv</span>
                        </div>
                        <span className="font-mono text-white">{network.bytes_recv_mb || 0} MB</span>
                    </div>
                </div>
            </Card>
        </div>
    );
}
