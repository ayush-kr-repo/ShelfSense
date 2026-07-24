import { useState, useEffect } from "react";
import { api } from "./api";
import Analytics from "./Analytics";
import Upload from "./Upload";
import { motion } from "framer-motion";

export default function Dashboard({ onLogout }) {
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  function loadWarehouses() {                          // ← now reusable
    api("/api/v1/warehouses")
      .then(setWarehouses)
      .catch(() => setWarehouses([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadWarehouses(); }, []);

  if (selectedId) return <Analytics id={selectedId} onBack={() => setSelectedId(null)} />;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Your Warehouses 📦</h1>
        <button onClick={onLogout} className="bg-slate-700 hover:bg-slate-600 rounded-lg px-4 py-2 text-sm">Log out</button>
      </div>

      <Upload onUploaded={loadWarehouses} />            {/* ← the form; refreshes list on success */}

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : warehouses.length === 0 ? (
        <p className="text-slate-400">No warehouses yet. Add one above. 👆</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {warehouses.map((w, i) => (
            <motion.div key={w.id} onClick={() => setSelectedId(w.id)}
                initial={{ opacity: 0, y: 20 }}                 // start: invisible, 20px down
                animate={{ opacity: 1, y: 0 }}                  // end: visible, in place
                transition={{ delay: i * 0.06, duration: 0.3 }} // each card slightly later → stagger
                className="bg-slate-800 rounded-2xl p-6 shadow-lg hover:ring-2 ring-blue-500 cursor-pointer transition">
                <h2 className="text-xl font-semibold">{w.name}</h2>
                <p className="text-slate-400 text-sm mt-1">ID: {w.id}</p>
                <p className="text-slate-500 text-xs mt-3">Added {new Date(w.created_at).toLocaleDateString()}</p>
            </motion.div>
            ))}

        </div>
      )}
    </div>
  );
}
