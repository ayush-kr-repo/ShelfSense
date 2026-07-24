import { useState } from "react";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();                       // stop the browser's default page reload
    setError("");
    try {
      // /login uses OAuth2 form data (username/password), NOT JSON:
      const body = new URLSearchParams({ username: email, password });
      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (!res.ok) throw new Error("Invalid email or password");
      const data = await res.json();
      localStorage.setItem("token", data.access_token);   // remember the JWT
      onLogin();                                            // tell App we're in
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center">
      <form onSubmit={handleSubmit}
            className="bg-slate-800 p-8 rounded-2xl shadow-xl w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-3xl font-bold text-center">ShelfSense 📦</h1>
        <p className="text-slate-400 text-center text-sm">Sign in to your warehouses</p>

        <input type="email" placeholder="Email" value={email}
               onChange={(e) => setEmail(e.target.value)}
               className="bg-slate-700 rounded-lg px-4 py-2 outline-none focus:ring-2 ring-blue-500" />
        <input type="password" placeholder="Password" value={password}
               onChange={(e) => setPassword(e.target.value)}
               className="bg-slate-700 rounded-lg px-4 py-2 outline-none focus:ring-2 ring-blue-500" />

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button type="submit"
                className="bg-blue-600 hover:bg-blue-500 rounded-lg px-4 py-2 font-semibold transition">
          Sign in
        </button>
      </form>
    </div>
  );
}
