import { useState } from "react";
import { api } from "./api";

export default function Upload({ onUploaded }) {
  const [id, setId] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!id || !file) return;
    setBusy(true);
    try {
      const form = new FormData();          // multipart — for sending files
      form.append("file", file);
      await api(`/api/v1/warehouse/${id}/upload`, { method: "POST", body: form });
      setId(""); setFile(null);
      onUploaded();                          // tell Dashboard to refresh the list
    } catch {
      alert("Upload failed");
    } finally {
      setBusy(false);
    }
  }

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
      <button type="submit" disabled={busy}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4 py-2 font-semibold transition">
        {busy ? "Uploading…" : "Add warehouse"}
      </button>
    </form>
  );
}
