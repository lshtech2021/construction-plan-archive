import React, { useRef, useState } from 'react';
import { Button } from './Button';

interface FileUploadProps {
  onFile: (file: File) => void;
  accept?: string;
  uploading?: boolean;
  label?: string;
}

export function FileUpload({
  onFile,
  accept = 'application/pdf',
  uploading = false,
  label = 'Upload PDF',
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = (file: File | undefined) => {
    if (file) onFile(file);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <svg
        className="mb-3 h-10 w-10 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
        />
      </svg>
      <p className="mb-2 text-sm text-gray-600">
        Drag and drop a PDF here, or
      </p>
      <Button
        variant="secondary"
        size="sm"
        loading={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {label}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
