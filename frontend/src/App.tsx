import { useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { Login } from "./pages/Login";
import { Cases } from "./pages/Cases";
import { CaseBuilder } from "./pages/CaseBuilder";
import { Submit } from "./pages/Submit";

export function App() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  const go = (path: string) => {
    navigate(path);
    setNavOpen(false);
  };

  const isActive = (path: string) =>
    path === "/submit"
      ? location.pathname === "/submit"
      : location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <div className={`app${navOpen ? " nav-open" : ""}`}>
      <header className="topbar">
        <div className="topbar-row">
          <button className="brand" onClick={() => go("/cases")}>
            <span className="mark">IP</span>
            IP Addressing Grader
          </button>
          <button
            className="nav-toggle"
            aria-label="Toggle navigation"
            aria-expanded={navOpen}
            onClick={() => setNavOpen((o) => !o)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
        <nav className={`topnav${navOpen ? " open" : ""}`}>
          <button
            className={`navlink${isActive("/cases") ? " active" : ""}`}
            onClick={() => go("/cases")}
          >
            Cases
          </button>
          <button
            className={`navlink${isActive("/submit") ? " active" : ""}`}
            onClick={() => go("/submit")}
          >
            Grade Submission
          </button>
          <button
            className="navlink danger"
            onClick={() => {
              logout();
              go("/login");
            }}
          >
            Logout
          </button>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/cases" element={<Cases />} />
          <Route path="/cases/new" element={<CaseBuilder />} />
          <Route path="/cases/:id/edit" element={<CaseBuilder />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="*" element={<Navigate to="/cases" replace />} />
        </Routes>
      </main>
    </div>
  );
}
