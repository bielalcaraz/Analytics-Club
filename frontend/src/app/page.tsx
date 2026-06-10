"use client";
import { useState, useCallback } from "react";
import UploadZone from "@/components/UploadZone";
import MappingReview from "@/components/MappingReview";
import PersonReview from "@/components/PersonReview";
import NormalizedTable from "@/components/NormalizedTable";
import Dashboard, { DashboardResponse, DashboardSpec } from "@/components/Dashboard";
import DashboardReview from "@/components/DashboardReview";

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

export type PersonGroup = {
  column_name: string;
  valores: string[];
  nombre_canonico: string;
  confianza: "alta" | "media";
};

export type NormalizedData = {
  columnas: string[];
  filas: Record<string, unknown>[];
  total_filas: number;
  schema: string;
  advertencias: string[];
  normalizaciones: Record<string, Record<string, string>>;
  posibles_duplicados: Record<string, string[][]>;
  grupos_personas?: PersonGroup[];
};

type Step = "upload" | "review" | "person-review" | "result" | "dashboard-review" | "dashboard";

export default function Home() {
  const [step, setStep] = useState<Step>("upload");
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null);
  const [normalizedData, setNormalizedData] = useState<NormalizedData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dashboardSpec, setDashboardSpec] = useState<DashboardSpec | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

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

      if (data.grupos_personas && data.grupos_personas.length > 0) {
        setStep("person-review");
      } else {
        setStep("result");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, [uploadData]);

  const handlePersonReview = useCallback(async (gruposConfirmados: PersonGroup[]) => {
    if (!normalizedData) return;
    setLoading(true);
    setError(null);

    try {
      // If no groups confirmed, skip the API call entirely
      if (gruposConfirmados.length === 0) {
        setStep("result");
        return;
      }

      const res = await fetch("/api/review-persons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          columnas: normalizedData.columnas,
          filas: normalizedData.filas,
          grupos_confirmados: gruposConfirmados,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error aplicando las unificaciones");
      }
      const updated = await res.json();
      setNormalizedData((prev) =>
        prev ? { ...prev, columnas: updated.columnas, filas: updated.filas, total_filas: updated.total_filas } : prev
      );
      setStep("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, [normalizedData]);

  const handleGenerateDashboard = useCallback(async () => {
    if (!normalizedData) return;
    setDashboardLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/dashboard/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ columnas: normalizedData.columnas, filas: normalizedData.filas }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error sugiriendo el dashboard");
      }
      const spec: DashboardSpec = await res.json();
      setDashboardSpec(spec);
      setStep("dashboard-review");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setDashboardLoading(false);
    }
  }, [normalizedData]);

  const handleConfirmDashboard = useCallback(async (spec: DashboardSpec) => {
    if (!normalizedData) return;
    setDashboardLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/dashboard/data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ columnas: normalizedData.columnas, filas: normalizedData.filas, spec }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error generando el dashboard");
      }
      const data: DashboardResponse = await res.json();
      setDashboardData(data);
      setStep("dashboard");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setDashboardLoading(false);
    }
  }, [normalizedData]);

  const handleReset = () => {
    setStep("upload");
    setUploadData(null);
    setNormalizedData(null);
    setDashboardSpec(null);
    setDashboardData(null);
    setError(null);
  };

  // Map internal steps to the 4 visual steps
  const visualStep =
    step === "dashboard-review" || step === "dashboard"
      ? "dashboard"
      : step === "result"
      ? "result"
      : step === "upload"
      ? "upload"
      : "review";
  const visualSteps = ["upload", "review", "result", "dashboard"] as const;
  const visualLabels = ["Subir Excel", "Revisar mapeo", "Datos normalizados", "Generar dashboard"];
  const visualStepIndex = visualSteps.indexOf(visualStep);

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
        {visualSteps.map((s, i) => {
          const active = visualStep === s;
          const done = i < visualStepIndex;
          return (
            <div key={s} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full transition-colors ${
                active ? "bg-gray-900 text-white" :
                done ? "bg-green-100 text-green-800" :
                "bg-gray-100 text-gray-400"
              }`}>
                <span>{done ? "✓" : i + 1}</span>
                <span>{visualLabels[i]}</span>
              </div>
              {i < visualSteps.length - 1 && <div className="w-6 h-px bg-gray-200" />}
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
      {step === "person-review" && normalizedData?.grupos_personas && (
        <PersonReview
          grupos={normalizedData.grupos_personas}
          onConfirm={handlePersonReview}
          loading={loading}
        />
      )}
      {step === "result" && normalizedData && (
        <>
          <NormalizedTable data={normalizedData} onReset={handleReset} />

          <div className="mt-6 flex justify-end">
            <button
              onClick={handleGenerateDashboard}
              disabled={dashboardLoading}
              className="bg-gray-900 text-white text-sm font-medium px-6 py-2.5 rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {dashboardLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generando dashboard...
                </>
              ) : (
                "Generar dashboard"
              )}
            </button>
          </div>
        </>
      )}
      {step === "dashboard-review" && normalizedData && dashboardSpec && (
        <DashboardReview
          spec={dashboardSpec}
          columns={normalizedData.columnas}
          onConfirm={handleConfirmDashboard}
          onBack={() => setStep("result")}
          loading={dashboardLoading}
        />
      )}
      {step === "dashboard" && dashboardData && (
        <>
          <Dashboard spec={dashboardData.spec} data={dashboardData.data} />
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep("dashboard-review")}
              className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              ← Editar gráficos
            </button>
            <button
              onClick={handleReset}
              className="bg-gray-900 text-white text-sm font-medium px-6 py-2.5 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Procesar otro Excel
            </button>
          </div>
        </>
      )}
    </main>
  );
}
