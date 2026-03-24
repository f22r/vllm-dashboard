import React from 'react';

export default function MobileNav({ activeTab, setActiveTab, connectionStatus }) {
    const Icon = ({ name, className }) => {
        switch (name) {
            case 'dashboard':
                return (
                    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                );
            case 'models':
                return (
                    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
                );
            case 'chat':
                return (
                    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                );
            case 'logs':
                return (
                    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16v16H4z"></path><path d="M4 8h16" /></svg>
                );
            default:
                return null;
        }
    };

    return (
        // Visible only on small screens
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-[92%] md:hidden">
            <div className="bg-surface/80 backdrop-blur-lg border border-white/5 rounded-2xl p-2 flex items-center justify-between">
                <button onClick={() => setActiveTab('dashboard')} className={`flex-1 flex flex-col items-center gap-1 py-2 ${activeTab === 'dashboard' ? 'text-primary' : 'text-gray-300'}`}>
                    <Icon name="dashboard" className="w-5 h-5" />
                    <span className="text-[11px]">Dash</span>
                </button>
                <button onClick={() => setActiveTab('models')} className={`flex-1 flex flex-col items-center gap-1 py-2 ${activeTab === 'models' ? 'text-accent' : 'text-gray-300'}`}>
                    <Icon name="models" className="w-5 h-5" />
                    <span className="text-[11px]">Models</span>
                </button>
                <button onClick={() => setActiveTab('chat')} className={`flex-1 flex flex-col items-center gap-1 py-2 ${activeTab === 'chat' ? 'text-green-400' : 'text-gray-300'}`}>
                    <Icon name="chat" className="w-5 h-5" />
                    <span className="text-[11px]">Chat</span>
                </button>
                <button onClick={() => setActiveTab('logs')} className={`flex-1 flex flex-col items-center gap-1 py-2 ${activeTab === 'logs' ? 'text-purple-400' : 'text-gray-300'}`}>
                    <Icon name="logs" className="w-5 h-5" />
                    <span className="text-[11px]">Logs</span>
                </button>
                <div className="ml-2 pl-2 border-l border-white/5 flex items-center">
                    <span className={`block h-2 w-2 rounded-full ${connectionStatus === 'connected' ? 'bg-success' : connectionStatus === 'connecting' ? 'bg-warning' : 'bg-danger'}`}></span>
                </div>
            </div>
        </div>
    );
}
