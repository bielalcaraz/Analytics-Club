"use client";
import { useState, useRef, DragEvent, ChangeEvent } from "react";

type Props = {
  onUpload: (file: File) => void;
  loading: boolean;
};

export default function UploadZone({ onUpload, loading }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      alert("Solo se aceptan archivos .xlsx y .xls");
      return;
    }
    onUpload(file);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onClick={() => !loading && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-colors ${
        dragging ? "border-gray-900 bg-gray-50" :
        loading ? "border-gray-200 bg-gray-50 cursor-not-allowed" :
        "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={onChange}
        disabled={loading}
      />

      {loading ? (
        <div>
          <div className="w-10 h-10 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600 font-medium">Analizando con IA...</p>
          <p className="text-gray-400 text-sm mt-1">Claude está mapeando las columnas</p>
        </div>
      ) : (
        <div>
          <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-gray-700 font-medium mb-1">Arrastra tu Excel aquí</p>
          <p className="text-gray-400 text-sm">o haz clic para seleccionar</p>
          <p className="text-gray-300 text-xs mt-3">.xlsx · .xls · máx. 20 MB</p>
        </div>
      )}
    </div>
  );
}
