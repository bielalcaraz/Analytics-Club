"use client";
import { NormalizedData } from "@/app/page";

type Props = {
  data: NormalizedData;
  onReset: () => void;
};

export default function NormalizedTable({ data, onReset }: Props) {
  const preview = data.filas.slice(0, 100);

  return (
    <div>
      {/* Success banner */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-green-900">
            Datos normalizados correctamente
          </p>
          <p className="text-xs text-green-700 mt-0.5">
            {data.total_filas.toLocaleString()} filas · {data.columnas.length} columnas · schema: {data.schema}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Total filas</p>
          <p className="text-2xl font-semibold text-gray-900">{data.total_filas.toLocaleString()}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Columnas normalizadas</p>
          <p className="text-2xl font-semibold text-gray-900">{data.columnas.length}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Schema detectado</p>
          <p className="text-sm font-semibold text-gray-900 font-mono mt-1">{data.schema}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-6">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700">
            Vista previa {data.total_filas > 100 ? "(primeras 100 filas)" : ""}
          </p>
          <span className="text-xs text-gray-400 font-mono">
            {data.columnas.join(" · ")}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {data.columnas.map((col) => (
                  <th key={col} className="text-left px-3 py-2.5 font-medium text-gray-500 font-mono whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.map((row, i) => (
                <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                  {data.columnas.map((col) => (
                    <td key={col} className="px-3 py-2 text-gray-600 whitespace-nowrap max-w-32 truncate">
                      {row[col] === null || row[col] === undefined ? (
                        <span className="text-gray-300">—</span>
                      ) : String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={onReset}
          className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          ← Procesar otro Excel
        </button>
        <p className="text-xs text-gray-400">
          Próximo paso: guardar en base de datos y generar KPIs
        </p>
      </div>
    </div>
  );
}
