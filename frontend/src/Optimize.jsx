import { useState } from "react";
import { api } from "./api";
import Twin from "./Twin";

export default function Optimize({ warehouseId }) {
  const [form, setForm] = useState({
    floorW: 10, floorD: 8,          // floor size in metres
    shelfW: 2.0, shelfD: 0.6,       // one shelf's footprint
    aisle: 0.9,                     // gap the solver keeps between shelves
  });
  const [layout, setLayout] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function set(field) {
    return (e) => setForm({ ...form, [field]: Number(e.target.value) });
  }

  async function runOptimize() {
    setBusy(true);
    setError("");
    try {
      // upper bound: how many shelves fit if we ignore aisles entirely.
      // The solver will place fewer — its count is the real answer.
      const maxCandidates = Math.floor(
        (form.floorW * form.floorD) / (form.shelfW * form.shelfD)
      );
      const count = Math.min(Math.max(maxCandidates, 1), 60); // cap: keep solve fast
      const shelves = Array.from({ length: count }, (_, i) => ({
        id: `S${i}`, w: form.shelfW, d: form.shelfD,
      }));
      const req = {
        floor_w_m: form.floorW, floor_d_m: form.floorD,
        shelves, aisle_m: form.aisle,
        exit_zone: [0, 0, 1.5, 1.5],   // 1.5 m exit corner always kept clear
      };
      const result = await api("/api/v1/optimize", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      setLayout(result);
    } catch {
      setError("Optimization failed — check your inputs (all values must be positive).");
    } finally { setBusy(false); }
  }

  // capacity numbers derived from what the solver actually placed
  const storageArea = layout
    ? layout.shelves.reduce((sum, s) => sum + s.w * s.d, 0)
    : 0;
  const floorArea = form.floorW * form.floorD;

  return (
    <div className="mt-10">
      <h2 className="text-xl font-semibold mb-4">Layout Planner</h2>

      <div className="bg-slate-800 rounded-2xl p-6 mb-4">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <Field label="Floor width (m)" value={form.floorW} onChange={set("floorW")} />
          <Field label="Floor depth (m)" value={form.floorD} onChange={set("floorD")} />
          <Field label="Shelf width (m)" value={form.shelfW} onChange={set("shelfW")} step="0.1" />
          <Field label="Shelf depth (m)" value={form.shelfD} onChange={set("shelfD")} step="0.1" />
          <Field label="Aisle width (m)" value={form.aisle} onChange={set("aisle")} step="0.1" />
        </div>
        <button onClick={runOptimize} disabled={busy}
                className="mt-4 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-5 py-2 text-sm font-semibold">
          {busy ? "Solving…" : "⚡ Plan my layout"}
        </button>
        {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      </div>

      {layout ? (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Stat label="Shelves that fit" value={layout.placed_count} />
            <Stat label="Storage area" value={`${storageArea.toFixed(1)} m²`} />
            <Stat label="Floor used" value={`${((storageArea / floorArea) * 100).toFixed(0)}%`} />
          </div>
          <p className="text-slate-500 text-xs mb-3">
            Aisles of {form.aisle} m kept between shelves · exit corner kept clear ·
            solver status: {layout.status}
          </p>
          <Twin layout={layout.shelves} />
        </>
      ) : (
        <p className="text-slate-500 text-sm">
          Enter your floor and shelf dimensions, then plan your layout.
        </p>
      )}
    </div>
  );
}

function Field({ label, value, onChange, step = "1" }) {
  return (
    <label className="text-sm">
      <span className="text-slate-400 block mb-1">{label}</span>
      <input type="number" min="0" step={step} value={value} onChange={onChange}
             className="w-full bg-slate-700 rounded-lg px-3 py-2 outline-none focus:ring-2 ring-blue-500" />
    </label>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 text-center">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-slate-400 text-xs mt-1">{label}</p>
    </div>
  );
}
