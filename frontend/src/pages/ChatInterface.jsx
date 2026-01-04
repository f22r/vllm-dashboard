import React, { useState, useEffect, useRef } from 'react';

export function ChatInterface() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [models, setModels] = useState([]);
    const [selectedModel, setSelectedModel] = useState('');
    const messagesEndRef = useRef(null);

    // Fetch running models on mount
    useEffect(() => {
        const fetchModels = async () => {
            try {
                const response = await fetch('/api/vllm/control/status');
                const data = await response.json();
                if (data.models && data.models.length > 0) {
                    setModels(data.models);
                    // Select first available model by default
                    if (!selectedModel) {
                        setSelectedModel(data.models[0].name);
                    }
                } else {
                    setModels([]);
                    setSelectedModel('');
                }
            } catch (error) {
                console.error("Failed to fetch status for chat:", error);
            }
        };

        fetchModels();
        // Poll for model availability every 5s
        const interval = setInterval(fetchModels, 5000);
        return () => clearInterval(interval);
    }, [selectedModel]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !selectedModel) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await fetch('/api/vllm/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: selectedModel,
                    messages: [...messages, userMessage]
                })
            });

            const data = await response.json();

            if (data.error) {
                setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }]);
            } else {
                // Assuming standard OpenAI format response
                const reply = data.choices?.[0]?.message?.content || "No response received.";
                setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
            }

        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', content: "Error: Failed to communicate with server." }]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="w-full max-w-6xl mx-auto h-[calc(100vh-80px)] flex flex-col pb-6">
            <header className="mb-4 flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-1">Live Chat</h1>
                    <p className="text-gray-400 text-sm">Interact with running models in real-time</p>
                </div>

                <div className="flex items-center gap-3 bg-surface/50 p-2 rounded-xl border border-white/10">
                    <span className="text-sm text-gray-400 pl-2">Model:</span>
                    <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="bg-black/20 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-primary min-w-[200px]"
                    >
                        {models.length === 0 ? (
                            <option value="">No models running</option>
                        ) : (
                            models.map(m => (
                                <option key={m.name} value={m.name}>
                                    {m.name} (Port {m.port})
                                </option>
                            ))
                        )}
                    </select>
                </div>
            </header>

            {/* Chat Area */}
            <div className="flex-1 glass-card overflow-hidden flex flex-col relative">
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                            <svg className="w-16 h-16 mb-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                            <p className="text-lg font-medium">Start a conversation</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] rounded-2xl px-5 py-4 ${msg.role === 'user'
                                    ? 'bg-primary text-white ml-12 rounded-tr-none'
                                    : 'bg-surface border border-white/10 text-gray-100 mr-12 rounded-tl-none'
                                }`}>
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-surface border border-white/10 text-gray-100 rounded-2xl rounded-tl-none px-5 py-4 flex items-center gap-2">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-white/5 bg-surface/30">
                    <div className="relative">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={!selectedModel || models.length === 0}
                            placeholder={!selectedModel ? "Start a model first..." : "Type your message... (Shift+Enter for new line)"}
                            className="w-full bg-black/20 border border-white/10 rounded-xl pl-4 pr-14 py-4 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 resize-none h-[60px] max-h-[120px]"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || loading || !selectedModel}
                            className="absolute right-2 top-2 p-2 bg-primary hover:bg-blue-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
