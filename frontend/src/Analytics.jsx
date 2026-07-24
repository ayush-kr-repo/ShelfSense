import { useState, useEffect } from "react";
import { api } from "./api";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { motion, useSpring, useTransform } from "framer-motion";

const bandColor = {
  Excellent: "text-green-400", Good: "text-blue-400",
  Fair: "text-yellow-400", Poor: "text-red-400",
};

export default function Analytics({ id, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/v1/analytics/${id}`)                    // ← calls YOUR analytics endpoint
      .then(setData)
      .catch(() => setError("Failed to load analytics"));
  }, [id]);

  if (error) return <Shell onBack={onBack}><p className="text-red-400">{error}</p></Shell>;
  if (!data) return <Shell onBack={onBack}><p className="text-slate-400">Analyzing…</p></Shell>;

  // turn the subscores object into an array the chart understands
  const chartData = Object.entries(data.health.subscores).map(([k, v]) => ({
    dimension: k.replace(/_/g, " "), value: v,
  }));

  return (
    <Shell onBack={onBack}>
      <h1 className="text-3xl font-bold mb-6">{id} · Analytics</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-2xl p-6 flex flex-col items-center justify-center">
          <p className="text-slate-400 text-sm">Health Score</p>
          <CountUp value={data.health.score} className={`text-6xl font-bold ${bandColor[data.health.band]}`} />
          <p className={`text-lg font-semibold ${bandColor[data.health.band]}`}>{data.health.band}</p>
          <p className="text-slate-400 text-sm mt-4">Storage Utilization: {data.sur}%</p>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6">
          <p className="text-slate-400 text-sm mb-2">Score Breakdown</p>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={chartData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.5} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <h2 className="text-xl font-semibold mt-8 mb-4">Recommendations</h2>
      {data.recommendations.length === 0 ? (
        <p className="text-slate-400">No issues found. 🎉</p>
      ) : (
        <div className="flex flex-col gap-3">
          {data.recommendations.map((r, i) => (
            <div key={i} className="bg-slate-800 rounded-xl p-4 border-l-4 border-blue-500">
              <p className="font-medium">{r.recommendation}</p>
              <p className="text-slate-400 text-sm mt-1">{r.condition}</p>
              <span className="text-xs bg-slate-700 rounded px-2 py-0.5 mt-2 inline-block">
                Impact: {r.impact}
              </span>
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}

function Shell({ children, onBack }) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <button onClick={onBack} className="text-slate-400 hover:text-slate-100 mb-6 text-sm">← Back</button>
      {children}
    </div>
  );
}

function CountUp({ value, className }) {
  const spring = useSpring(0, { duration: 900 });
  const display = useTransform(spring, (v) => Math.round(v));
  useEffect(() => { spring.set(value); }, [value, spring]);
  return <motion.span className={className}>{display}</motion.span>;
}

