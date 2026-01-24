'use client';

import { useState, useEffect, useCallback } from 'react';

type Mode = 'work' | 'shortBreak' | 'longBreak';

const SETTINGS = {
  work: 25 * 60,
  shortBreak: 5 * 60,
  longBreak: 15 * 60,
};

const MODE_COLORS = {
  work: 'bg-red-500',
  shortBreak: 'bg-teal-500',
  longBreak: 'bg-blue-500',
};

export default function Pomodoro() {
  const [mode, setMode] = useState<Mode>('work');
  const [timeLeft, setTimeLeft] = useState(SETTINGS.work);
  const [isActive, setIsActive] = useState(false);

  const resetTimer = useCallback((newMode: Mode = mode) => {
    setIsActive(false);
    setMode(newMode);
    setTimeLeft(SETTINGS[newMode]);
  }, [mode]);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      setIsActive(false);
      // Optional: Play sound or send notification
      if (typeof window !== 'undefined') {
        alert(`Time's up for ${mode}!`);
      }
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, timeLeft, mode]);

  const toggleTimer = () => setIsActive(!isActive);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <main className={`min-h-screen flex flex-col items-center justify-center transition-colors duration-500 ${MODE_COLORS[mode]} text-white p-4`}>
      <div className="bg-white/10 backdrop-blur-md p-8 rounded-3xl shadow-2xl w-full max-w-md border border-white/20">
        <div className="flex justify-center gap-2 mb-8">
          {(['work', 'shortBreak', 'longBreak'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => resetTimer(m)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === m ? 'bg-white/20 shadow-inner' : 'hover:bg-white/10'
              }`}
            >
              {m === 'work' ? 'Pomodoro' : m === 'shortBreak' ? 'Short Break' : 'Long Break'}
            </button>
          ))}
        </div>

        <div className="text-center mb-12">
          <div className="text-9xl font-bold tracking-tighter tabular-nums mb-4">
            {formatTime(timeLeft)}
          </div>
          <div className="text-xl opacity-80 font-medium uppercase tracking-widest">
            {mode === 'work' ? 'Focus Time' : 'Time to Rest'}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <button
            onClick={toggleTimer}
            className="w-full py-4 bg-white text-gray-900 rounded-2xl text-2xl font-bold shadow-lg active:scale-95 transition-transform uppercase tracking-wider"
          >
            {isActive ? 'Pause' : 'Start'}
          </button>
          
          <button
            onClick={() => resetTimer()}
            className="w-full py-2 text-white/60 hover:text-white transition-colors font-medium"
          >
            Reset
          </button>
        </div>
      </div>

      <footer className="mt-8 text-white/40 text-sm">
        Stay focused, stay productive.
      </footer>
    </main>
  );
}

