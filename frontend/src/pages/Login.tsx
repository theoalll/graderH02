import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiError } from "../api";
import { Theme, ThemeToggle } from "../theme";
import { toast } from "../toast";

export function Login({ theme, onTheme }: { theme: Theme; onTheme: (t: Theme) => void }) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate("/cases");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Sign-in failed");
    }
  };

  return (
    <div className="login-wrap page">
      <form className="panel login-card" onSubmit={submit}>
        <div className="login-top">
          <button className="brand brand-static" type="button" tabIndex={-1}>
            <img className="mark" src="/logo.svg" alt="" width={32} height={32} />
            IP Addressing Grader
          </button>
          <ThemeToggle theme={theme} onChange={onTheme} />
        </div>
        <h1>Sign in</h1>
        <p className="muted login-sub">
          Enter the TA account credentials to continue.
        </p>

        <div className="field">
          <label className="field-label">Username</label>
          <input
            value={username}
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div className="field">
          <label className="field-label">Password</label>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button className="btn primary btn-block" type="submit">
          Sign in
        </button>
      </form>
    </div>
  );
}
