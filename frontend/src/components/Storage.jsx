import React from 'react';

export function Storage({ disks }) {
    if (!disks || !Array.isArray(disks) || disks.length === 0) return null;

    let totalUsed = 0;
    let totalFree = 0;
    let totalSize = 0;

    disks.forEach(disk => {
        totalUsed += disk.used_gb || 0;
        totalFree += disk.free_gb || 0;
        totalSize += disk.total_gb || 0;
    });

    const percent = totalSize > 0 ? Math.round((totalUsed / totalSize) * 100) : 0;
    const isHigh = percent > 85;

    return (
        <div className="glass-card p-6 mb-8 group hover:border-primary/20 transition-colors">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <ellipse cx="12" cy="5" rx="9" ry="3" />
                            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                        </svg>
                    </div>
                    <h3 className="text-gray-200 font-medium">Storage Usage</h3>
                </div>
                <span className={`text-xl font-bold ${isHigh ? 'text-danger' : 'text-gray-200'}`}>
                    {percent}%
                </span>
            </div>

            <div className="h-3 w-full bg-surfaceHighlight rounded-full overflow-hidden mb-3">
                <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${isHigh ? 'bg-gradient-to-r from-red-500 to-orange-500' : 'bg-gradient-to-r from-blue-500 to-violet-500'
                        }`}
                    style={{ width: `${percent}%` }}
                ></div>
            </div>

            <div className="flex justify-between text-sm text-gray-400 font-mono">
                <span>{totalUsed.toFixed(1)} GB used</span>
                <span>{totalFree.toFixed(1)} GB free</span>
            </div>
        </div>
    );
}
