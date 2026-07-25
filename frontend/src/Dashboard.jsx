import { useState, useEffect } from "react";
import { api } from "./api";
import Analytics from "./Analytics";
import Upload from "./Upload";
import { motion } from "framer-motion";

export default function Dashboard({ onLogout }) {
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  function loadWarehouses() {
    api("/api/v1/warehouses")
      .then(setWarehouses)
      .catch(() => setWarehouses([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadWarehouses(); }, []);

  async function renameWarehouse(e, w) {
    e.stopPropagation();                       // don't open Analytics underneath
    const name = window.prompt("New name:", w.name);
    if (!name || name === w.name) return;
    await api(`/api/v1/warehouse/${w.id}/meta`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    loadWarehouses();
  }

  async function editDimensions(e, w) {
    e.stopPropagation();
    const current = w.dimensions ? `${w.dimensions.length} x ${w.dimensions.width}` : "";
    const input = window.prompt("Floor size in metres, length x width (e.g. 10 x 8):", current);
    if (!input) return;
    const parts = input.toLowerCase().split("x").map((p) => Number(p.trim()));
    if (parts.length !== 2 || parts.some((n) => !n || n <= 0)) {
      window.alert("Couldn't read that — use the format: 10 x 8");
      return;
    }
    await api(`/api/v1/warehouse/${w.id}/meta`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ length_m: parts[0], width_m: parts[1] }),
    });
    loadWarehouses();
  }

  async function deleteWarehouse(e, w) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${w.name}" and its photo? This can't be undone.`)) return;
    await api(`/api/v1/warehouse/${w.id}`, { method: "DELETE" });
    loadWarehouses();
  }

  if (selectedId) return <Analytics id={selectedId} onBack={() => setSelectedId(null)} />;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Your Warehouses 📦</h1>
        <button onClick={onLogout} className="bg-slate-700 hover:bg-slate-600 rounded-lg px-4 py-2 text-sm">Log out</button>
      </div>

      <Upload onUploaded={loadWarehouses} />

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : warehouses.length === 0 ? (
        <p className="text-slate-400">No warehouses yet. Add one above. 👆</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {warehouses.map((w, i) => (
            <motion.div key={w.id} onClick={() => setSelectedId(w.id)}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.3 }}
                className="bg-slate-800 rounded-2xl p-6 shadow-lg hover:ring-2 ring-blue-500 cursor-pointer transition">
                <div className="flex justify-between items-start">
                  <h2 className="text-xl font-semibold">{w.name}</h2>
                  <div className="flex gap-1">
                    <IconBtn title="Rename" onClick={(e) => renameWarehouse(e, w)}>✏️</IconBtn>
                    <IconBtn title="Edit floor size" onClick={(e) => editDimensions(e, w)}>📐</IconBtn>
                    <IconBtn title="Delete" onClick={(e) => deleteWarehouse(e, w)}>🗑️</IconBtn>
                  </div>
                </div>
                <p className="text-slate-400 text-sm mt-1">ID: {w.id}</p>
                <p className="text-slate-400 text-sm mt-1">
                  {w.dimensions
                    ? `${w.dimensions.length} × ${w.dimensions.width} m floor`
                    : "No floor size set 📐"}
                </p>
                <p className="text-slate-500 text-xs mt-3">Added {new Date(w.created_at).toLocaleDateString()}</p>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

function IconBtn({ title, onClick, children }) {
  return (
    <button title={title} onClick={onClick}
            className="hover:bg-slate-700 rounded-lg px-2 py-1 text-sm transition">
      {children}
    </button>
  );
}
