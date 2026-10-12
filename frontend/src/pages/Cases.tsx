import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { CaseSummary } from "../types";

export function Cases() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<CaseSummary | null>(null);

  const load = () => {
    setLoading(true);
    api
      .listCases()
      .then(setCases)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  useEffect(() => {
    if (!pending) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPending(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending]);

  const confirmDelete = async () => {
    if (!pending) return;
    await api.deleteCase(pending.case_id);
    setPending(null);
    load();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2 className="page-title">Cases</h2>
          <p className="page-sub">IP-addressing labs available for grading.</p>
        </div>
        <button className="btn primary" onClick={() => navigate("/cases/new")}>
          New Case
        </button>
      </div>

      {error && <div className="alert error"><span className="alert-ico" /><span>{error}</span></div>}

      {loading ? (
        <div className="empty">Loading cases…</div>
      ) : cases.length === 0 ? (
        <div className="empty">No cases yet. Create one to start grading submissions.</div>
      ) : (
        <div className="cases-grid">
          {cases.map((c) => (
            <div className="case-card" key={c.case_id}>
              <div className="case-card-body">
                <h3 className="case-card-title">{c.title}</h3>
              </div>
              <div className="case-card-actions">
                <button className="btn sm secondary" onClick={() => navigate(`/cases/${c.case_id}/edit`)}>
                  Edit
                </button>
                <button className="btn sm primary" onClick={() => navigate(`/submit?case=${c.case_id}`)}>
                  Grade
                </button>
                <button className="btn sm danger" onClick={() => setPending(c)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pending && (
        <div className="modal-backdrop" onClick={() => setPending(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Confirm delete case" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ fontSize: 16 }}>Delete case</h3>
              <button className="btn icon ghost" onClick={() => setPending(null)} aria-label="Close">✕</button>
            </div>
            <p className="muted" style={{ marginTop: 0 }}>
              Delete <b>{pending.title}</b>? This action cannot be undone.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <button className="btn ghost" onClick={() => setPending(null)}>Cancel</button>
              <button className="btn danger" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
