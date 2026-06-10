"use client";
import { useState } from "react";
import { ChartSpec, DashboardSpec } from "@/components/Dashboard";

type Props = {
  spec: DashboardSpec;
  columns: string[];
  onConfirm: (spec: DashboardSpec) => void;
  onBack: () => void;
  loading: boolean;
};

const CHART_TYPES: ChartSpec["chart_type"][] = ["kpi_card", "line", "bar", "pie", "table"];
const AGGREGATIONS: ChartSpec["aggregation"][] = ["sum", "mean", "count", "min", "max"];

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

function confianzaNivel(confidence: number): keyof typeof confianzaStyle {
  if (confidence >= 0.8) return "alta";
  if (confidence >= 0.5) return "media";
  return "baja";
}

let manualChartCounter = 0;

function buildManualChart(columns: string[]): ChartSpec {
  manualChartCounter += 1;
  return {
    id: `chart_manual_${Date.now()}_${manualChartCounter}`,
    title: "Nuevo gráfico",
    chart_type: "bar",
    dimension: columns[0] ?? null,
    granularity: null,
    measure: columns[0] ?? "",
    aggregation: "sum",
    confidence: 1.0,
    rationale: "Gráfico añadido manualmente.",
  };
}

export default function DashboardReview({ spec, columns, onConfirm, onBack, loading }: Props) {
  const [charts, setCharts] = useState<ChartSpec[]>(spec.charts);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());

  const updateChart = (i: number, changes: Partial<ChartSpec>) => {
    setCharts((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...changes } : c)));
  };

  const addChart = () => {
    setCharts((prev) => [...prev, buildManualChart(columns)]);
  };

  const removeChart = (id: string) => {
    setCharts((prev) => prev.filter((c) => c.id !== id));
    setExcluded((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleChartTypeChange = (i: number, chart_type: ChartSpec["chart_type"]) => {
    if (chart_type === "kpi_card") {
      updateChart(i, { chart_type, dimension: null, granularity: null });
    } else if (charts[i].dimension === null) {
      updateChart(i, { chart_type, dimension: columns[0] ?? null });
    } else {
      updateChart(i, { chart_type });
    }
  };

  const toggleExcluded = (id: string) => {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleConfirm = () => {
    onConfirm({ charts: charts.filter((c) => !excluded.has(c.id)) });
  };

  const incluidos = charts.length - excluded.size;

  return (
    <div>
      {/* Info banner */}
      {charts.length > 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">
              Claude propuso <strong>{charts.length} gráficos</strong> para este dashboard
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Revisa y ajusta cada gráfico — {incluidos} de {charts.length} se incluirán
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4 text-yellow-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86l-8.18 14.18A1 1 0 003 19.5h18a1 1 0 00.89-1.46L13.71 3.86a1 1 0 00-1.42 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">
              Claude no encontró gráficos válidos para este dataset
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Puedes construir el dashboard manualmente añadiendo gráficos abajo.
            </p>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="space-y-3 mb-6">
        {charts.map((chart, i) => {
          const isExcluded = excluded.has(chart.id);
          const nivel = confianzaNivel(chart.confidence);
          return (
            <div
              key={chart.id}
              className={`bg-white border border-gray-200 rounded-xl p-4 transition-opacity ${isExcluded ? "opacity-50" : ""}`}
            >
              {/* Title row */}
              <div className="flex items-start gap-3 mb-3">
                <input
                  type="checkbox"
                  checked={!isExcluded}
                  onChange={() => toggleExcluded(chart.id)}
                  title="Incluir en el dashboard"
                  className="w-4 h-4 mt-2 rounded border-gray-300 flex-shrink-0"
                />
                <input
                  type="text"
                  value={chart.title}
                  onChange={(e) => updateChart(i, { title: e.target.value })}
                  disabled={isExcluded}
                  className="flex-1 font-medium text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                />
                <span className={`text-xs px-2 py-1 rounded border whitespace-nowrap ${confianzaStyle[nivel]}`}>
                  {confianzaLabel[nivel]}
                </span>
                <button
                  onClick={() => removeChart(chart.id)}
                  title="Eliminar gráfico"
                  className="text-gray-400 hover:text-red-600 transition-colors px-1"
                >
                  ✕
                </button>
              </div>

              {/* Config row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Tipo</label>
                  <select
                    value={chart.chart_type}
                    onChange={(e) => handleChartTypeChange(i, e.target.value as ChartSpec["chart_type"])}
                    disabled={isExcluded}
                    className="w-full text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                  >
                    {CHART_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Dimensión</label>
                  <select
                    value={chart.dimension ?? ""}
                    onChange={(e) => updateChart(i, { dimension: e.target.value || null })}
                    disabled={isExcluded || chart.chart_type === "kpi_card"}
                    className="w-full font-mono text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                  >
                    {chart.chart_type === "kpi_card" ? (
                      <option value="">—</option>
                    ) : (
                      columns.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Medida</label>
                  <select
                    value={chart.measure}
                    onChange={(e) => updateChart(i, { measure: e.target.value })}
                    disabled={isExcluded}
                    className="w-full font-mono text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                  >
                    {columns.map((col) => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Agregación</label>
                  <select
                    value={chart.aggregation}
                    onChange={(e) => updateChart(i, { aggregation: e.target.value as ChartSpec["aggregation"] })}
                    disabled={isExcluded}
                    className="w-full text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                  >
                    {AGGREGATIONS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Granularity (only relevant for non-kpi charts) */}
              {chart.chart_type !== "kpi_card" && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Granularidad</label>
                    <select
                      value={chart.granularity ?? ""}
                      onChange={(e) =>
                        updateChart(i, { granularity: (e.target.value || null) as ChartSpec["granularity"] })
                      }
                      disabled={isExcluded}
                      className="w-full text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 bg-white disabled:bg-gray-50"
                    >
                      <option value="">Sin agrupar</option>
                      <option value="day">Día</option>
                      <option value="week">Semana</option>
                      <option value="month">Mes</option>
                    </select>
                  </div>
                </div>
              )}

              {chart.rationale && (
                <p className="text-xs text-gray-400">{chart.rationale}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Add chart */}
      <div className="mb-6">
        <button
          onClick={addChart}
          disabled={columns.length === 0}
          className="w-full border border-dashed border-gray-300 rounded-xl py-3 text-sm text-gray-500 hover:text-gray-700 hover:border-gray-400 transition-colors disabled:opacity-50"
        >
          + Añadir gráfico
        </button>
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
          disabled={loading || incluidos === 0}
          className="bg-gray-900 text-white text-sm font-medium px-6 py-2.5 rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generando dashboard...
            </>
          ) : (
            "Confirmar dashboard →"
          )}
        </button>
      </div>
    </div>
  );
}
