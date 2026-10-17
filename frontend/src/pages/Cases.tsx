import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { CaseSummary } from "../types";
import { toast } from "../toast";

export function Cases() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<CaseSummary | null>(null);
  const [leaving, setLeaving] = useState(false);
  const closing = useRef(false);

  // Play the exit animation before the dialog is removed from the tree.
  const closeConfirm = useCallback(() => {
    if (closing.current) return;
    closing.current = true;
    setLeaving(true);
    window.setTimeout(() => {
      setPending(null);
      setLeaving(false);
      closing.current = false;
    }, 220);
  }, []);

  const load = () => {
    setLoading(true);
    api
      .listCases()
      .then(setCases)
      .catch((e) => toast("error", e instanceof ApiError ? e.message : "Could not load cases"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  useEffect(() => {
    if (!pending) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending, closeConfirm]);

  const confirmDelete = async () => {
    if (!pending) return;
    try {
      await api.deleteCase(pending.case_id);
      toast("info", `Case "${pending.title}" was deleted.`);
      closeConfirm();
      load();
    } catch (e) {
      toast("error", e instanceof ApiError ? e.message : "Could not delete the case");
      closeConfirm();
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2 className="page-title">Cases</h2>
          <p className="page-sub">IP-addressing lab definitions used for grading submissions.</p>
        </div>
        <button className="btn primary" onClick={() => navigate("/cases/new")}>
          New case
        </button>
      </div>

      {loading ? (
        <div className="empty">Loading cases…</div>
      ) : cases.length === 0 ? (
        <div className="empty">No cases yet. Create a case to start grading submissions.</div>
      ) : (
        <div className="cases-grid">
          {cases.map((c) => (
            <div className="case-card" key={c.case_id}>
              <div className="case-card-body">
                <h3 className="case-card-title">{c.title}</h3>
                {(c.base_block || c.method || c.subnet_count != null) && (
                  <p className="case-card-meta">
                    {c.base_block && <span className="mono">{c.base_block}</span>}
                    {c.base_block && (c.method || c.subnet_count != null) && " · "}
                    {c.method && <span>{c.method}</span>}
                    {c.method && c.subnet_count != null && " · "}
                    {c.subnet_count != null && (
                      <span>{c.subnet_count} {c.subnet_count === 1 ? "subnet" : "subnets"}</span>
                    )}
                  </p>
                )}
              </div>
              <div className="case-card-actions">
                <button className="btn sm primary" onClick={() => navigate(`/submit?case=${c.case_id}`)}>
                  Grade
                </button>
                <button className="btn sm secondary" onClick={() => navigate(`/cases/${c.case_id}/edit`)}>
                  Edit
                </button>
                <button
                  className="btn sm icon danger"
                  onClick={() => setPending(c)}
                  aria-label={`Delete ${c.title}`}
                  title="Delete"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pending && (
        <div className={`modal-backdrop${leaving ? " leaving" : ""}`} onClick={closeConfirm}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Confirm delete case" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 className="modal-title">Delete case</h3>
              <button className="btn icon ghost" onClick={closeConfirm} aria-label="Close">✕</button>
            </div>
            <p className="muted flush-top">
              Delete <b>{pending.title}</b>? This cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="btn ghost" onClick={closeConfirm}>Cancel</button>
              <button className="btn danger" onClick={confirmDelete}>Delete case</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
