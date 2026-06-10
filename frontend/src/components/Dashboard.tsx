"use client";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export type ChartSpec = {
  id: string;
  title: string;
  chart_type: "line" | "bar" | "pie" | "kpi_card" | "table";
  dimension?: string | null;
  granularity?: "day" | "week" | "month" | null;
  measure: string;
  aggregation: "sum" | "mean" | "count" | "min" | "max";
  confidence: number;
  rationale: string;
};

export type DashboardSpec = {
  charts: ChartSpec[];
};

export type ChartPoint = {
  label: string | number | null;
  value: number | null;
};

export type ChartData =
  | { value: number | null }
  | { data: ChartPoint[] };

export type DashboardResponse = {
  spec: DashboardSpec;
  data: Record<string, ChartData>;
};

const COLORS = ["#111827", "#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#db2777"];

function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return value.toLocaleString("es-ES", { maximumFractionDigits: 2 });
  }
  return value;
}

function ChartRenderer({ chart, chartData }: { chart: ChartSpec; chartData: ChartData }) {
  if (chart.chart_type === "kpi_card") {
    const value = "value" in chartData ? chartData.value : null;
    return <p className="text-3xl font-semibold text-gray-900 mt-2">{formatValue(value)}</p>;
  }

  const rows = "data" in chartData ? chartData.data : [];

  if (rows.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">Sin datos para este gráfico</p>;
  }

  if (chart.chart_type === "table") {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-3 py-2 font-medium text-gray-500 font-mono">
                {chart.dimension ?? "categoría"}
              </th>
              <th className="text-right px-3 py-2 font-medium text-gray-500 font-mono">
                {chart.measure}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-600">{formatValue(row.label)}</td>
                <td className="px-3 py-2 text-gray-600 text-right">{formatValue(row.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (chart.chart_type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={90} label>
            {rows.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => formatValue(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chart.chart_type === "bar") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-25} textAnchor="end" height={50} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => formatValue(v)} />
          <Bar dataKey="value" fill="#111827" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // line
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number) => formatValue(v)} />
        <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

type Props = {
  spec: DashboardSpec;
  data: Record<string, ChartData>;
};

export default function Dashboard({ spec, data }: Props) {
  const kpiCharts = spec.charts.filter((c) => c.chart_type === "kpi_card");
  const otherCharts = spec.charts.filter((c) => c.chart_type !== "kpi_card");

  return (
    <div>
      {/* KPI cards row */}
      {kpiCharts.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {kpiCharts.map((chart) => {
            const chartData = data[chart.id];
            if (!chartData) return null;
            return (
              <div key={chart.id} className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-xs text-gray-500">{chart.title}</p>
                <ChartRenderer chart={chart} chartData={chartData} />
              </div>
            );
          })}
        </div>
      )}

      {/* Remaining charts */}
      {otherCharts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {otherCharts.map((chart) => {
            const chartData = data[chart.id];
            if (!chartData) return null;
            return (
              <div key={chart.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-700">{chart.title}</p>
                </div>
                <div className="p-4">
                  <ChartRenderer chart={chart} chartData={chartData} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
