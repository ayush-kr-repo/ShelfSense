import { useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  function logout(){
    localStorage.removeItem("token");
    setToken(null);
  }

  if (!token) return <Login onLogin={() => setToken(localStorage.getItem("token"))} />;
  return <Dashboard onLogout={logout} />;
}
export default App;
