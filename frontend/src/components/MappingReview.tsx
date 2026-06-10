"use client";
import { useState } from "react";
import { UploadResponse, MappingResult, ColumnMapping } from "@/app/page";

type Props = {
  uploadData: UploadResponse;
  onConfirm: (mapping: MappingResult) => void;
  onBack: () => void;
  loading: boolean;
};

const TIPOS = ["string", "float", "integer", "date", "boolean"];

const confianzaStyle = {
  alta: "bg-green-50 text-green-700 border-green-200",
  media: "bg-yellow-50 text-yellow-700 border-yellow-200",
  baja: "bg-red-50 text-red-700 border-red-200",
};

const confianzaLabel = {
  alta: "Alta",
  media: "Media — revisa",
  baja: "Baja — verifica",
};

export default function MappingReview({ uploadData, onConfirm, onBack, loading }: Props) {
  const [columnas, setColumnas] = useState<ColumnMapping[]>(
    uploadData.mapping.columnas
  );

  const updateCol = (i: number, field: keyof ColumnMapping, value: string) => {
    setColumnas((prev) => prev.map((c, idx) => idx === i ? { ...c, [field]: value } : c));
  };

  const handleConfirm = () => {
    onConfirm({ columnas, schema_detectado: uploadData.mapping.schema_detectado });
  };

  const alertas = columnas.filter((c) => c.confianza !== "alta").length;

  return (
    <div>
      {/* Info banner */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 flex items-start gap-3">
        <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">
            Claude detectó <strong>{columnas.length} columnas</strong> en {uploadData.total_rows.toLocaleString()} filas
            {" · "}schema: <span className="font-mono text-xs bg-gray-200 px-1.5 py-0.5 rounded">{uploadData.mapping.schema_detectado}</span>
          </p>
          {alertas > 0 && (
            <p className="text-sm text-yellow-700 mt-1">
              {alertas} columna{alertas > 1 ? "s" : ""} con confianza media o baja — revísalas antes de continuar
            </p>
          )}
        </div>
      </div>

      {/* Mapping table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Columna original</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Nombre destino</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Tipo</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Confianza</th>
            </tr>
          </thead>
          <tbody>
            {columnas.map((col, i) => (
              <tr
                key={i}
                className={`border-b border-gray-50 last:border-0 ${
                  col.confianza !== "alta" ? "bg-yellow-50/30" : ""
                }`}
              >
                <td className="px-4 py-3">
                  <span className="font-mono text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {col.origen}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <input
                    type="text"
                    value={col.destino}
                    onChange={(e) => updateCol(i, "destino", e.target.value)}
                    className="w-full font-mono text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white"
                  />
                </td>
                <td className="px-4 py-3">
                  <select
                    value={col.tipo}
                    onChange={(e) => updateCol(i, "tipo", e.target.value)}
                    className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white"
                  >
                    {TIPOS.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <div>
                    <span className={`text-xs px-2 py-1 rounded border ${confianzaStyle[col.confianza]}`}>
                      {confianzaLabel[col.confianza]}
                    </span>
                    {col.nota && (
                      <p className="text-xs text-gray-400 mt-1">{col.nota}</p>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          disabled={loading}
          className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          ← Volver
        </button>
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="bg-gray-900 text-white text-sm font-medium px-6 py-2.5 rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Transformando...
            </>
          ) : (
            "Confirmar y transformar →"
          )}
        </button>
      </div>
    </div>
  );
}
