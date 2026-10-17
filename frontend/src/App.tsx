import { useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { ThemeToggle, useTheme } from "./theme";
import { ToastHost } from "./toast";
import { Login } from "./pages/Login";
import { Cases } from "./pages/Cases";
import { CaseBuilder } from "./pages/CaseBuilder";
import { Submit } from "./pages/Submit";

export function App() {
  const { token, logout } = useAuth();
  const [theme, setTheme] = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  const go = (path: string) => {
    navigate(path);
    setNavOpen(false);
  };

  const isActive = (path: string) =>
    path === "/submit"
      ? location.pathname === "/submit"
      : location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <>
      <ToastHost />
      {!token ? (
        <div className="page-anim" key={location.pathname}>
          <Routes>
            <Route path="/login" element={<Login theme={theme} onTheme={setTheme} />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      ) : (
        <div className={`app${navOpen ? " nav-open" : ""}`}>
          <header className="topbar">
            <div className="topbar-row">
              <button className="brand" onClick={() => go("/cases")}>
                <img className="mark" src="/logo.svg" alt="" width={32} height={32} />
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
                Grade submission
              </button>
              <ThemeToggle theme={theme} onChange={setTheme} />
              <button
                className="navlink danger"
                onClick={() => {
                  logout();
                  go("/login");
                }}
              >
                Sign out
              </button>
            </nav>
          </header>
          <main className="content">
            <div className="page-anim" key={location.pathname}>
              <Routes>
                <Route path="/cases" element={<Cases />} />
                <Route path="/cases/new" element={<CaseBuilder />} />
                <Route path="/cases/:id/edit" element={<CaseBuilder />} />
                <Route path="/submit" element={<Submit />} />
                <Route path="*" element={<Navigate to="/cases" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      )}
    </>
  );
}
