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
      {/* Warnings banner */}
      {data.advertencias?.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-yellow-400 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-yellow-900">Advertencias del proceso</p>
              <ul className="mt-1 space-y-0.5">
                {data.advertencias.map((msg, i) => (
                  <li key={i} className="text-xs text-yellow-800">• {msg}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Similar references warning */}
      {data.posibles_duplicados && Object.keys(data.posibles_duplicados).length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-orange-400 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-orange-900">Referencias posiblemente duplicadas</p>
              <p className="text-xs text-orange-700 mt-0.5 mb-2">
                Estas referencias podrían ser la misma pieza — verifica con tu equipo antes de usar los datos.
              </p>
              {Object.entries(data.posibles_duplicados).map(([col, groups]) => (
                <div key={col} className="mt-1">
                  <span className="text-xs font-mono font-medium text-orange-800">{col}: </span>
                  {groups.map((group, i) => (
                    <span key={i} className="inline-flex items-center gap-1 mr-2">
                      <span className="text-orange-400 text-xs">▸</span>
                      {group.map((ref, j) => (
                        <span key={ref}>
                          {j > 0 && <span className="text-orange-300 text-xs"> / </span>}
                          <span className="text-xs font-mono bg-orange-100 text-orange-800 px-1 rounded">{ref}</span>
                        </span>
                      ))}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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

      {/* Text normalization collapsible */}
      {data.normalizaciones && Object.keys(data.normalizaciones).length > 0 && (
        <details className="mb-4 bg-gray-50 border border-gray-200 rounded-xl overflow-hidden">
          <summary className="px-4 py-3 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100 select-none list-none flex items-center justify-between">
            <span>Texto normalizado por IA <span className="font-normal text-gray-400">({Object.keys(data.normalizaciones).length} columna(s))</span></span>
            <span className="text-gray-400 text-xs">▼</span>
          </summary>
          <div className="px-4 pb-4 pt-1 space-y-1.5 border-t border-gray-200">
            {Object.entries(data.normalizaciones).map(([col, changes]) => (
              <div key={col} className="text-xs">
                <span className="font-mono text-gray-500 font-medium">{col}:</span>{" "}
                <span className="text-gray-500">
                  {Object.entries(changes).map(([orig, norm], i) => (
                    <span key={orig}>
                      {i > 0 && <span className="text-gray-300"> · </span>}
                      <span className="text-gray-400">{orig}</span>
                      <span className="text-gray-300"> → </span>
                      <span className="text-gray-600">{norm}</span>
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

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
