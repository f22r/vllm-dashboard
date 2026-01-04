import React from 'react';

const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 52; // radius = 52

export function Gauge({ percent, label, unit = '%', size = 'normal', colorClass = 'text-primary' }) {
    const offset = GAUGE_CIRCUMFERENCE - (percent / 100) * GAUGE_CIRCUMFERENCE;
    const isMini = size === 'mini';

    return (
        <div className={`relative flex flex-col items-center justify-center ${isMini ? 'w-24 h-24' : 'w-40 h-40'}`}>
            <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 120 120">
                {/* Background Circle */}
                <circle
                    className="text-surfaceHighlight"
                    strokeWidth="10"
                    stroke="currentColor"
                    fill="transparent"
                    r="52"
                    cx="60"
                    cy="60"
                />
                {/* Progress Circle */}
                <circle
                    className={`${colorClass} transition-all duration-1000 ease-out`}
                    strokeWidth="10"
                    strokeDasharray={GAUGE_CIRCUMFERENCE}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="52"
                    cx="60"
                    cy="60"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="flex items-baseline">
                    <span className={`font-bold ${isMini ? 'text-xl' : 'text-3xl'} text-white`}>{percent}</span>
                    <span className={`ml-0.5 text-gray-400 ${isMini ? 'text-xs' : 'text-sm'}`}>{unit}</span>
                </div>
                {label && <span className="text-xs text-gray-500 mt-1 uppercase tracking-wide">{label}</span>}
            </div>
        </div>
    );
}
