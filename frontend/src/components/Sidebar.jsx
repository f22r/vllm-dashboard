import React from 'react';

const Logo = () => (
    <svg className="w-8 h-8 text-primary" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);

const DashboardIcon = () => (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7"></rect>
        <rect x="14" y="3" width="7" height="7"></rect>
        <rect x="14" y="14" width="7" height="7"></rect>
        <rect x="3" y="14" width="7" height="7"></rect>
    </svg>
);

const ModelIcon = () => (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
        <line x1="12" y1="22.08" x2="12" y2="12"></line>
    </svg>
);

export function Sidebar({ activeTab, setActiveTab, connectionStatus }) {
    return (
        <div className="w-64 glass h-full flex flex-col border-r border-white/10 z-20">
            <div className="p-6 flex items-center space-x-3 border-b border-white/5">
                <Logo />
                <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-violet-500">
                    vLLM Dash
                </span>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                <button
                    onClick={() => setActiveTab('dashboard')}
                    className={`nav-item w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${activeTab === 'dashboard'
                        ? 'bg-primary/20 text-primary border border-primary/20 shadow-[0_0_15px_rgba(59,130,246,0.2)]'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                >
                    <DashboardIcon />
                    <span className="font-medium">Dashboard</span>
                </button>
                <button
                    onClick={() => setActiveTab('models')}
                    className={`nav-item w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${activeTab === 'models'
                        ? 'bg-accent/20 text-accent border border-accent/20 shadow-[0_0_15px_rgba(139,92,246,0.2)]'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                >
                    <ModelIcon />
                    <span className="font-medium">Models</span>
                </button>
                <button
                    onClick={() => setActiveTab('chat')}
                    className={`nav-item w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${activeTab === 'chat'
                        ? 'bg-green-500/20 text-green-400 border border-green-500/20 shadow-[0_0_15px_rgba(74,222,128,0.2)]'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    <span className="font-medium">Chat</span>
                </button>
            </nav>

            <div className="p-4 border-t border-white/5">
                <div className="glass-card p-4 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400 uppercase tracking-wider">Status</span>
                        <span className={`flex h-2 w-2 rounded-full ${connectionStatus === 'connected' ? 'bg-success shadow-[0_0_10px_#10b981]' :
                            connectionStatus === 'connecting' ? 'bg-warning animate-pulse' : 'bg-danger'
                            }`}></span>
                    </div>
                    <div className="text-sm font-medium text-gray-200">
                        {connectionStatus === 'connected' ? 'System Online' : 'Connecting...'}
                    </div>
                </div>
            </div>
        </div>
    );
}
