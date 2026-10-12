import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiError } from "../api";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/cases");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    }
  };

  return (
    <div className="login-wrap">
      <form className="panel login-card" onSubmit={submit}>
        <button className="brand" type="button" style={{ pointerEvents: "none" }}>
          <span className="mark">IP</span>
          IP Addressing Grader
        </button>
        <h1>Sign in</h1>
        <p className="muted" style={{ marginTop: 4, marginBottom: 20 }}>
          Use the teaching-assistant credentials to continue.
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

        {error && <div className="alert error"><span className="alert-ico" /><span>{error}</span></div>}
        <button className="btn primary" type="submit" style={{ width: "100%" }}>
          Sign in
        </button>
        <p className="login-foot">Single shared TA account · grading is not stored.</p>
      </form>
    </div>
  );
}
