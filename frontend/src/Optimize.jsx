import { useState } from "react";
import { api } from "./api";
import Twin from "./Twin";

export default function Optimize({ floorDims, currentShelves = 0 }) {
  const [form, setForm] = useState({
    floorW: floorDims?.length ?? 10,      // real dims when set, else defaults
    floorD: floorDims?.width ?? 8,
    shelfW: 2.0, shelfD: 0.6,
    aisle: 0.9,
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
      const maxCandidates = Math.floor(
        (form.floorW * form.floorD) / (form.shelfW * form.shelfD)
      );
      const count = Math.min(Math.max(maxCandidates, 1), 60);
      const shelves = Array.from({ length: count }, (_, i) => ({
        id: `S${i}`, w: form.shelfW, d: form.shelfD,
      }));
      const req = {
        floor_w_m: form.floorW, floor_d_m: form.floorD,
        shelves, aisle_m: form.aisle, cell_m: 0.2,
        exit_zone: [0, 0, 1.5, 1.5],
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

  const fits = layout ? layout.placed_count : 0;
  const delta = fits - currentShelves;
  const shelfArea = layout && layout.shelves.length
    ? layout.shelves[0].w * layout.shelves[0].d : 0;

  return (
    <div className="mt-10">
      <h2 className="text-xl font-semibold mb-4">Capacity Planner</h2>

      <div className="bg-slate-800 rounded-2xl p-6 mb-4">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <Field label="Floor width (m)" value={form.floorW} onChange={set("floorW")} />
          <Field label="Floor depth (m)" value={form.floorD} onChange={set("floorD")} />
          <Field label="Shelf width (m)" value={form.shelfW} onChange={set("shelfW")} step="0.1" />
          <Field label="Shelf depth (m)" value={form.shelfD} onChange={set("shelfD")} step="0.1" />
          <Field label="Aisle width (m)" value={form.aisle} onChange={set("aisle")} step="0.1" />
        </div>
        {!floorDims && (
          <p className="text-yellow-500/80 text-xs mt-3">
            ⚠ No floor size saved for this warehouse — using defaults. Set it from the dashboard card for real numbers.
          </p>
        )}
        <button onClick={runOptimize} disabled={busy}
                className="mt-4 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-5 py-2 text-sm font-semibold">
          {busy ? "Solving…" : "⚡ Plan my layout"}
        </button>
        {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      </div>

      {layout && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Stat label="Shelves detected now (approx)" value={`~${currentShelves}`} />
            <Stat label="This floor can fit" value={fits} />
            {delta > 0 ? (
              <Stat label="Room to grow" accent
                    value={`+${delta} shelves ≈ +${(delta * shelfArea).toFixed(1)} m²`} />
            ) : (
              <Stat label="Capacity status" value="At solver capacity" />
            )}
          </div>
          <p className="text-slate-500 text-xs mb-3">
            <span className="text-green-400">■</span> existing (approx) ·{" "}
            <span className="text-amber-400">■</span> room to grow ·
            aisles {form.aisle} m · exit corner kept clear · solver: {layout.status}
          </p>
          <Twin layout={layout.shelves} floorW={form.floorW} floorD={form.floorD}
                existingCount={currentShelves} />
        </>
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

function Stat({ label, value, accent }) {
  return (
    <div className={`rounded-xl p-4 text-center ${accent ? "bg-amber-500/10 ring-1 ring-amber-500/40" : "bg-slate-800"}`}>
      <p className={`text-2xl font-bold ${accent ? "text-amber-400" : ""}`}>{value}</p>
      <p className="text-slate-400 text-xs mt-1">{label}</p>
    </div>
  );
}
