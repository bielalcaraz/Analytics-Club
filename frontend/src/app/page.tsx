"use client";
import { useState, useCallback } from "react";
import UploadZone from "@/components/UploadZone";
import MappingReview from "@/components/MappingReview";
import NormalizedTable from "@/components/NormalizedTable";

export type ColumnMapping = {
  origen: string;
  destino: string;
  tipo: string;
  formato?: string;
  limpieza?: string;
  confianza: "alta" | "media" | "baja";
  nota?: string;
};

export type MappingResult = {
  columnas: ColumnMapping[];
  schema_detectado: string;
};

export type UploadResponse = {
  file_id: string;
  headers: string[];
  sample_rows: Record<string, unknown>[];
  mapping: MappingResult;
  total_rows: number;
};

export type NormalizedData = {
  columnas: string[];
  filas: Record<string, unknown>[];
  total_filas: number;
  schema: string;
};

type Step = "upload" | "review" | "result";

export default function Home() {
  const [step, setStep] = useState<Step>("upload");
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null);
  const [normalizedData, setNormalizedData] = useState<NormalizedData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error subiendo el archivo");
      }
      const data: UploadResponse = await res.json();
      setUploadData(data);
      setStep("review");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleConfirm = useCallback(async (mapping: MappingResult) => {
    if (!uploadData) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_id: uploadData.file_id, mapping }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error transformando los datos");
      }
      const data: NormalizedData = await res.json();
      setNormalizedData(data);
      setStep("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, [uploadData]);

  const handleReset = () => {
    setStep("upload");
    setUploadData(null);
    setNormalizedData(null);
    setError(null);
  };

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-2xl font-semibold text-gray-900">Dataplant</h1>
        <p className="text-gray-500 text-sm mt-1">
          Sube tu Excel y la IA detectará y normalizará las columnas automáticamente
        </p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-8">
        {(["upload", "review", "result"] as Step[]).map((s, i) => {
          const labels = ["Subir Excel", "Revisar mapeo", "Datos normalizados"];
          const active = step === s;
          const done = (step === "review" && i === 0) || (step === "result" && i < 2);
          return (
            <div key={s} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full transition-colors ${
                active ? "bg-gray-900 text-white" :
                done ? "bg-green-100 text-green-800" :
                "bg-gray-100 text-gray-400"
              }`}>
                <span>{done ? "✓" : i + 1}</span>
                <span>{labels[i]}</span>
              </div>
              {i < 2 && <div className="w-6 h-px bg-gray-200" />}
            </div>
          );
        })}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Step content */}
      {step === "upload" && (
        <UploadZone onUpload={handleUpload} loading={loading} />
      )}
      {step === "review" && uploadData && (
        <MappingReview
          uploadData={uploadData}
          onConfirm={handleConfirm}
          onBack={handleReset}
          loading={loading}
        />
      )}
      {step === "result" && normalizedData && (
        <NormalizedTable data={normalizedData} onReset={handleReset} />
      )}
    </main>
  );
}
