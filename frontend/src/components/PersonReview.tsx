"use client";
import { useState } from "react";
import { PersonGroup } from "@/app/page";

type GroupDecision = {
  approved: boolean;
  nombre_canonico: string;
};

type Props = {
  grupos: PersonGroup[];
  onConfirm: (gruposConfirmados: PersonGroup[]) => void;
  loading: boolean;
};

export default function PersonReview({ grupos, onConfirm, loading }: Props) {
  const [decisions, setDecisions] = useState<Record<number, GroupDecision>>(
    () =>
      Object.fromEntries(
        grupos.map((g, i) => [i, { approved: true, nombre_canonico: g.nombre_canonico }])
      )
  );

  const setApproved = (i: number, approved: boolean) =>
    setDecisions((prev) => ({ ...prev, [i]: { ...prev[i], approved } }));

  const setCanonico = (i: number, nombre_canonico: string) =>
    setDecisions((prev) => ({ ...prev, [i]: { ...prev[i], nombre_canonico } }));

  const handleConfirm = () => {
    const confirmed: PersonGroup[] = grupos
      .filter((_, i) => decisions[i]?.approved)
      .map((g, i) => ({ ...g, nombre_canonico: decisions[i].nombre_canonico }));
    onConfirm(confirmed);
  };

  const approvedCount = Object.values(decisions).filter((d) => d.approved).length;

  return (
    <div>
      {/* Header banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-blue-900">
            Se detectaron {grupos.length} posible{grupos.length > 1 ? "s" : ""} duplicado{grupos.length > 1 ? "s" : ""} en columnas de personas
          </p>
          <p className="text-xs text-blue-700 mt-0.5">
            Confirma cuáles son la misma persona. Solo se unificarán los grupos que apruebes.
          </p>
        </div>
      </div>

      {/* Groups */}
      <div className="space-y-4 mb-6">
        {grupos.map((group, i) => {
          const dec = decisions[i];
          const isApproved = dec?.approved;
          return (
            <div
              key={i}
              className={`border rounded-xl p-4 transition-colors ${
                isApproved
                  ? "border-blue-200 bg-blue-50/30"
                  : "border-gray-200 bg-gray-50/50 opacity-60"
              }`}
            >
              {/* Column label */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Columna</span>
                <span className="font-mono text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">
                  {group.column_name}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded border ${
                  group.confianza === "alta"
                    ? "bg-green-50 text-green-700 border-green-200"
                    : "bg-yellow-50 text-yellow-700 border-yellow-200"
                }`}>
                  {group.confianza}
                </span>
              </div>

              {/* Question */}
              <p className="text-sm text-gray-700 mb-2">
                ¿Estas entradas se refieren a la misma persona?
              </p>

              {/* Values */}
              <div className="flex flex-wrap gap-2 mb-3">
                {group.valores.map((v) => (
                  <span
                    key={v}
                    className="font-mono text-sm bg-white border border-gray-200 text-gray-700 px-2.5 py-1 rounded-lg"
                  >
                    {v}
                  </span>
                ))}
              </div>

              {/* Canonical selector — only visible when approved */}
              {isApproved && (
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs text-gray-500">Nombre final:</span>
                  <select
                    value={dec.nombre_canonico}
                    onChange={(e) => setCanonico(i, e.target.value)}
                    className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:border-blue-400 font-mono"
                  >
                    {group.valores.map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                  <span className="text-xs text-gray-400">
                    (solo valores originales — sin inventar)
                  </span>
                </div>
              )}

              {/* Decision buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => setApproved(i, true)}
                  className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
                    isApproved
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-600 border-gray-300 hover:border-blue-400 hover:text-blue-600"
                  }`}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Sí, unificar
                </button>
                <button
                  onClick={() => setApproved(i, false)}
                  className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
                    !isApproved
                      ? "bg-gray-700 text-white border-gray-700"
                      : "bg-white text-gray-600 border-gray-300 hover:border-gray-500 hover:text-gray-700"
                  }`}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  No, son personas distintas
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => onConfirm([])}
          disabled={loading}
          className="text-sm text-gray-400 hover:text-gray-600 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Omitir todo
        </button>
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="bg-gray-900 text-white text-sm font-medium px-6 py-2.5 rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Aplicando...
            </>
          ) : (
            <>
              {approvedCount > 0
                ? `Aplicar ${approvedCount} unificación${approvedCount > 1 ? "es" : ""} →`
                : "Continuar sin cambios →"}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
