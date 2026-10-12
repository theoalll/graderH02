import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { CaseSchema, GradeReport, SolveResult } from "../types";
import { ExpectedTable } from "../components/ExpectedTable";
import { GradeReportView } from "../components/GradeReport";

// Configurable pattern used to detect the student NPM from the uploaded file name,
// e.g. "H02_2306165660.pkt" -> "2306165660". Override via VITE_NPM_FILENAME_REGEX.
const NPM_FILENAME_PATTERN = new RegExp(
  (import.meta as any).env?.VITE_NPM_FILENAME_REGEX || "H02[_-]?(\\d{4,})",
  "i"
);

export function Submit() {
  const [params] = useSearchParams();
  const [cases, setCases] = useState<CaseSchema[]>([]);
  const [caseId, setCaseId] = useState(params.get("case") || "");
  const [npm, setNpm] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [solve, setSolve] = useState<SolveResult | null>(null);
  const [report, setReport] = useState<GradeReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listCases()
      .then((cs) => {
        setCases(cs as unknown as CaseSchema[]);
        if (!caseId && cs.length) setCaseId(cs[0].case_id);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "load failed"));
  }, [caseId]);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    if (!f) return;
    const m = f.name.match(NPM_FILENAME_PATTERN);
    if (m) {
      setNpm(m[1]);
      setError("");
    } else {
      setNpm("");
      setError(
        `NPM not detected in filename "${f.name}". Please enter the student NPM manually.`
      );
    }
  };

  const run = async () => {
    setError("");
    if (!caseId) return setError("Select a case");
    if (!npm.trim()) return setError("Enter student NPM");
    if (!file) return setError("Upload a .pkt file");
    setBusy(true);
    try {
      const full = await api.getCase(caseId);
      const s = await api.solve(full, npm.trim());
      setSolve(s);
      const g = await api.grade(full, npm.trim(), file);
      setReport(g);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2 className="page-title">Grade Submission</h2>
          <p className="page-sub">Upload a Packet Tracer file to grade against a case.</p>
        </div>
      </div>

      {error && <div className="alert error"><span className="alert-ico" /><span>{error}</span></div>}

      <div className="panel">
        <div className="field-grid">
          <div className="field">
            <label className="field-label">Case</label>
            <select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              {cases.map((c) => (
                <option key={c.case_id} value={c.case_id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label">Student NPM</label>
            <input
              className="mono-input"
              value={npm}
              onChange={(e) => setNpm(e.target.value)}
              placeholder="e.g. 2406123456"
            />
          </div>
        </div>
          <div className="field">
            <label className="field-label">Packet Tracer file (.pkt)</label>
            <input type="file" accept=".pkt,.pka,.xml" onChange={onFile} />
            <p className="field-hint">
              NPM is auto-detected from the file name (pattern{" "}
              <span className="mono">H02_&#123;NPM&#125;</span>). If not found, enter it manually.
            </p>
          </div>
        <button className="btn primary" onClick={run} disabled={busy} style={{ width: "100%" }}>
          {busy ? "Working…" : "Solve & Grade"}
        </button>
      </div>

      {solve && (
        <section className="section" style={{ marginTop: 28 }}>
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h3 style={{ fontSize: 16 }}>Expected IP Addressing</h3>
            <span className="badge neutral">NPM {solve.npm}</span>
          </div>
          <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
            Resolved vars: <span className="mono">{JSON.stringify(solve.resolved_vars)}</span>
            {" · "}Total addresses used: <span className="mono">{solve.total_addresses_used}</span>
            {" · "}Fits base block:{" "}
            <span className={`badge ${solve.fits_base_block ? "pass" : "fail"}`}>
              <span className="dot" />
              {String(solve.fits_base_block)}
            </span>
          </p>
          <ExpectedTable subnets={solve.subnets} />
        </section>
      )}

      {report && <GradeReportView report={report} />}
    </div>
  );
}
