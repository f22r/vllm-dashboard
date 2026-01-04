import { useState, useEffect, useRef, useCallback } from 'react';

const RECONNECT_INTERVAL = 3000;

export function useWebSocket() {
    const [data, setData] = useState(null);
    const [status, setStatus] = useState('connecting'); // connecting, connected, disconnected
    const ws = useRef(null);
    const reconnectTimeout = useRef(null);

    const connect = useCallback(() => {
        // If already connected or connecting, do nothing
        if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
            return;
        }

        setStatus('connecting');
        const wsUrl = `ws://${window.location.host}/ws/monitoring`;

        // In development mode, might need to adjust port if proxy isn't doing it, 
        // but vite proxy should handle it if correctly configured.
        // However, for safety in this specific env, let's trust window.location.host for now as per original code.

        try {
            ws.current = new WebSocket(wsUrl);

            ws.current.onopen = () => {
                console.log('✅ WebSocket connected');
                setStatus('connected');
                if (reconnectTimeout.current) {
                    clearTimeout(reconnectTimeout.current);
                    reconnectTimeout.current = null;
                }
            };

            ws.current.onmessage = (event) => {
                try {
                    const parsedData = JSON.parse(event.data);
                    setData(parsedData);
                } catch (error) {
                    console.error('Failed to parse WebSocket data:', error);
                }
            };

            ws.current.onclose = () => {
                console.log('❌ WebSocket disconnected');
                setStatus('disconnected');
                scheduleReconnect();
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                setStatus('disconnected');
            };
        } catch (error) {
            console.error('Failed to connect:', error);
            setStatus('disconnected');
            scheduleReconnect();
        }
    }, []);

    const scheduleReconnect = useCallback(() => {
        if (reconnectTimeout.current) return;
        reconnectTimeout.current = setTimeout(() => {
            reconnectTimeout.current = null;
            connect();
        }, RECONNECT_INTERVAL);
    }, [connect]);

    useEffect(() => {
        connect();

        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
                    connect();
                }
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            if (ws.current) {
                ws.current.close();
            }
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [connect]);

    return { data, status };
}
