import { useState } from "react";
import { api } from "./api";
import Twin from "./Twin";

export default function Optimize({ warehouseId }) {
  const [layout, setLayout] = useState(null);
  const [busy, setBusy] = useState(false);

    async function runOptimize() {
    setBusy(true);
    try {
      const shelves = Array.from({ length: 14 }, (_, i) => ({ id: `S${i}`, w: 2.0, d: 0.6 }));
      const req = { floor_w_m: 10, floor_d_m: 8, shelves, exit_zone: [0, 0, 1.5, 1.5] };
      const result = await api("/api/v1/optimize", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      setLayout(result);
    } finally { setBusy(false); }
  }


  return (
    <div className="mt-10">
      <div className="flex items-center gap-4 mb-4">
        <h2 className="text-xl font-semibold">Recommended Layout</h2>
        <button onClick={runOptimize} disabled={busy}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold">
          {busy ? "Solving…" : "⚡ Optimize"}
        </button>
      </div>
      {layout ? (
        <>
          <p className="text-slate-400 text-sm mb-3">
            Maximum-capacity layout for a standard 10 × 8 m floor · {layout.status} · {layout.placed_count} shelves
          </p>
          <Twin layout={layout.shelves} />
        </>
      ) : (
        <p className="text-slate-500 text-sm">Click Optimize to generate a layout and view it in 3D.</p>
      )}
    </div>
  );
}
