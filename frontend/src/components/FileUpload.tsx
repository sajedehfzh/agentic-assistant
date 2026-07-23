import { useRef, useState } from 'react';

interface Props {
  onSelected: (file: File) => void;
  disabled?: boolean;
}

export default function FileUpload({ onSelected, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [filename, setFilename] = useState<string | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setFilename(file.name);
      onSelected(file);
    }
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,video/mp4,.mp3,.wav,.m4a,.mp4,.webm,.ogg,.flac"
        style={{ display: 'none' }}
        onChange={handleChange}
        disabled={disabled}
      />
      <div className="actions">
        <button
          type="button"
          className="ghost"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          Choose audio file…
        </button>
        {filename && <span className="muted">{filename}</span>}
      </div>
      <p className="muted" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
        Supported: mp3, wav, m4a, mp4, webm, ogg, flac. Consent is required before upload.
      </p>
    </div>
  );
}
