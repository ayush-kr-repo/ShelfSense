import { useState } from "react";
import { api } from "./api";

export default function Upload({ onUploaded }) {
  const [id, setId] = useState("");
  const [file, setFile] = useState(null);
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!id || !file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (length) form.append("length_m", length);       // ← send dims if provided
      if (width) form.append("width_m", width);
      if (height) form.append("height_m", height);
      await api(`/api/v1/warehouse/${id}/upload`, { method: "POST", body: form });
      setId(""); setFile(null); setLength(""); setWidth(""); setHeight("");
      onUploaded();
    } catch {
      alert("Upload failed");
    } finally {
      setBusy(false);
    }
  }

  const numCls = "bg-slate-700 rounded-lg px-3 py-2 w-24 outline-none focus:ring-2 ring-blue-500";

  return (
    <form onSubmit={handleSubmit}
          className="bg-slate-800 rounded-2xl p-6 mb-8 flex flex-wrap items-end gap-4">
      <div className="flex flex-col gap-1">
        <label className="text-slate-400 text-sm">Warehouse ID</label>
        <input value={id} onChange={(e) => setId(e.target.value)} placeholder="wh_office"
               className="bg-slate-700 rounded-lg px-3 py-2 outline-none focus:ring-2 ring-blue-500" />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-slate-400 text-sm">Photo</label>
        <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])}
               className="text-slate-300 text-sm" />
      </div>

      {/* real-world dimensions (optional) */}
      <div className="flex flex-col gap-1">
        <label className="text-slate-400 text-sm">Length (m)</label>
        <input type="number" step="0.1" value={length} onChange={(e) => setLength(e.target.value)}
               placeholder="20" className={numCls} />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-slate-400 text-sm">Width (m)</label>
        <input type="number" step="0.1" value={width} onChange={(e) => setWidth(e.target.value)}
               placeholder="12" className={numCls} />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-slate-400 text-sm">Height (m)</label>
        <input type="number" step="0.1" value={height} onChange={(e) => setHeight(e.target.value)}
               placeholder="4" className={numCls} />
      </div>

      <button type="submit" disabled={busy}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4 py-2 font-semibold transition">
        {busy ? "Uploading…" : "Add warehouse"}
      </button>
    </form>
  );
}
