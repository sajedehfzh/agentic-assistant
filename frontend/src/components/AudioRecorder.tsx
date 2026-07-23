import { useEffect, useRef, useState } from 'react';

interface Props {
  onRecorded: (blob: Blob, mimeType: string) => void;
  disabled?: boolean;
}

function formatTime(seconds: number): string {
  const mm = Math.floor(seconds / 60).toString().padStart(2, '0');
  const ss = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${mm}:${ss}`;
}

export default function AudioRecorder({ onRecorded, disabled }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [level, setLevel] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const tickRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  function cleanup() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (tickRef.current) window.clearInterval(tickRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close().catch(() => {});
    streamRef.current = null;
    audioCtxRef.current = null;
    analyserRef.current = null;
  }

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType =
        ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg', 'audio/mp4'].find((m) =>
          MediaRecorder.isTypeSupported(m),
        ) || '';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const finalType = recorder.mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: finalType });
        chunksRef.current = [];
        onRecorded(blob, finalType);
        cleanup();
      };

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const sum = data.reduce((acc, v) => acc + v, 0);
        const avg = sum / data.length;
        setLevel(Math.min(1, avg / 128));
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);

      startTimeRef.current = Date.now();
      setElapsed(0);
      tickRef.current = window.setInterval(() => {
        setElapsed((Date.now() - startTimeRef.current) / 1000);
      }, 250);

      recorder.start(1000);
      setIsRecording(true);
    } catch (err) {
      setError(`Microphone access failed: ${(err as Error).message}`);
      cleanup();
    }
  }

  function stop() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  return (
    <div className="recorder">
      {error && <div className="error-banner">{error}</div>}
      <div className="row" style={{ alignItems: 'center' }}>
        <div className="actions">
          {!isRecording ? (
            <button type="button" onClick={start} disabled={disabled}>
              Start recording
            </button>
          ) : (
            <button type="button" onClick={stop} className="danger">
              Stop
            </button>
          )}
        </div>
        <div className="timer">{formatTime(elapsed)}</div>
      </div>
      <div className="level">
        <div style={{ width: `${Math.round(level * 100)}%` }} />
      </div>
      <p className="muted" style={{ fontSize: '0.85rem', margin: 0 }}>
        Records meeting audio in your browser. When you stop, it is uploaded for processing.
      </p>
    </div>
  );
}
