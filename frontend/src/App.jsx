import React, { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { Sidebar } from './components/Sidebar';
import MobileNav from './components/MobileNav';
import { Dashboard } from './pages/Dashboard';
import { ModelManager } from './pages/ModelManager';
import { Logs } from './pages/Logs';
import { ChatInterface } from './pages/ChatInterface';

function App() {
    const { data, status } = useWebSocket();
    const [activeTab, setActiveTab] = useState('dashboard');

    return (
        <div className="flex h-screen bg-background text-white overflow-hidden font-sans">
            <Sidebar
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                connectionStatus={status}
            />

            <main className="flex-1 overflow-y-auto p-4 md:p-8 relative pb-20 md:pb-8">
                {/* Background Gradients */}
                <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
                    <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[120px]"></div>
                    <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-accent/20 blur-[120px]"></div>
                </div>

                {activeTab === 'dashboard' ? (
                    <Dashboard data={data} />
                ) : activeTab === 'models' ? (
                    <ModelManager data={data} />
                ) : activeTab === 'logs' ? (
                    <Logs />
                ) : (
                    <ChatInterface />
                )}
                <MobileNav activeTab={activeTab} setActiveTab={setActiveTab} connectionStatus={status} />
            </main>
        </div>
    );
}

export default App;
