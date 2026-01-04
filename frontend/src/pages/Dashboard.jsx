import React from 'react';
import { VllmStatus } from '../components/VllmStatus';
import { SystemStats } from '../components/SystemStats';
import { Storage } from '../components/Storage';

export function Dashboard({ data }) {
    if (!data) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                    <span className="text-gray-400 animate-pulse">Initializing Dashboard...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full max-w-7xl mx-auto pb-10">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">System Overview</h1>
                <p className="text-gray-400">Real-time monitoring of vLLM performance and system resources</p>
            </header>

            <VllmStatus data={data} />
            <SystemStats system={data.system} />
            <Storage disks={data.system?.disks} />
        </div>
    );
}
