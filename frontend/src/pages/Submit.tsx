import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { AllocationOrder, CaseSchema, GradeReport, SolveResult } from "../types";
import { ExpectedTable } from "../components/ExpectedTable";
import { GradeReportView } from "../components/GradeReport";
import { PrefixRecommendation } from "../components/PrefixRecommendation";
import { toast } from "../toast";

// Configurable pattern used to detect the student NPM from the uploaded file name,
// e.g. "H02_2306165660.pkt" -> "2306165660". Override via VITE_NPM_FILENAME_REGEX.
const NPM_FILENAME_PATTERN = new RegExp(
  (import.meta as any).env?.VITE_NPM_FILENAME_REGEX || "H02[_-]?(\\d{4,})",
  "i"
);

// A student NPM is exactly 10 digits and digits only.
const NPM_PATTERN = /^\d{10}$/;

const ORDER_OPTIONS: { value: AllocationOrder; title: string; sub: string }[] = [
  {
    value: "host_desc",
    title: "Host needs, largest first",
    sub: "Sort by how many hosts each subnet needs, biggest first. Equal sizes follow code order A to Z.",
  },
  {
    value: "code_desc",
    title: "Subnet code, Z to A",
    sub: "Sort equal-size subnets by their code, from Z to A. Larger subnets still come first.",
  },
];

const ORDER_TITLES: Record<AllocationOrder, string> = {
  host_desc: "Host needs, largest first",
  code_desc: "Subnet code, Z to A",
};

// Real steps of a grading run, shown under the button while it works.
const STAGE_LABELS = [
  "Fetching case",
  "Solving the answer key",
  "Grading the submission",
];

export function Submit() {
  const [params] = useSearchParams();
  const [cases, setCases] = useState<CaseSchema[]>([]);
  const [caseId, setCaseId] = useState(params.get("case") || "");
  const [npm, setNpm] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [allocationOrder, setAllocationOrder] = useState<AllocationOrder>("host_desc");
  const [solve, setSolve] = useState<SolveResult | null>(null);
  const [report, setReport] = useState<GradeReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);

  const npmDigits = npm.trim();
  const npmInvalid = npmDigits.length > 0 && !NPM_PATTERN.test(npmDigits);

  // Numbers only; length is validated rather than capped so the rule is visible.
  const onNpm = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNpm(e.target.value.replace(/\D/g, ""));
  };

  useEffect(() => {
    api
      .listCases()
      .then((cs) => {
        setCases(cs as unknown as CaseSchema[]);
        if (!caseId && cs.length) setCaseId(cs[0].case_id);
      })
      .catch((e) =>
        toast("error", e instanceof ApiError ? e.message : "Could not load cases")
      );
  }, [caseId]);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setSolve(null);
    setReport(null);
    if (!f) return;
    const found = f.name.match(NPM_FILENAME_PATTERN)?.[1] ?? "";
    if (NPM_PATTERN.test(found)) {
      setNpm(found);
    } else {
      setNpm("");
      toast(
        "warning",
        found
          ? `"${found}" in the file name is not a valid NPM. Enter the 10-digit student NPM below.`
          : `The NPM was not found in "${f.name}". Enter the student NPM below.`
      );
    }
  };

  const onOrder = (v: AllocationOrder) => {
    setAllocationOrder(v);
    setSolve(null);
    setReport(null);
  };

  const run = async () => {
    if (!caseId) return toast("error", "Choose a case first.");
    if (!npmDigits) return toast("error", "Enter the student NPM.");
    if (npmInvalid) return toast("error", "NPM must be exactly 10 digits.");
    if (!file) return toast("error", "Upload a Packet Tracer file.");
    setBusy(true);
    setStage(1);
    try {
      const full = await api.getCase(caseId);
      setStage(2);
      const s = await api.solve(full, npm.trim(), allocationOrder);
      setSolve(s);
      setStage(3);
      const g = await api.grade(full, npm.trim(), file, allocationOrder);
      setReport(g);
    } catch (e) {
      toast("error", e instanceof ApiError ? e.message : "Grading failed");
    } finally {
      setBusy(false);
      setStage(0);
    }
  };

  const orderValue = (solve?.allocation_order ?? allocationOrder) as AllocationOrder;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2 className="page-title">Grade submission</h2>
          <p className="page-sub">Upload a student Packet Tracer file and grade it against a case.</p>
        </div>
      </div>

      <div className="block">
        <div className="block-head">
          <div>
            <div className="block-title">
              <span className="step-num" aria-hidden="true">1</span>
              Submission
            </div>
            <p className="block-sub">Choose the case, confirm the student NPM, and upload the file.</p>
          </div>
        </div>
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
            <label className="field-label" htmlFor="student-npm">Student NPM</label>
            <input
              id="student-npm"
              className={`mono-input${npmInvalid ? " invalid" : ""}`}
              value={npm}
              onChange={onNpm}
              inputMode="numeric"
              autoComplete="off"
              aria-invalid={npmInvalid}
              aria-describedby={npmInvalid ? "npm-error" : "npm-hint"}
              placeholder="e.g. 2406123456"
            />
            {npmInvalid ? (
              <p className="field-error" id="npm-error">
                NPM must be exactly 10 digits.
              </p>
            ) : (
              <p className="field-hint" id="npm-hint">
                Exactly 10 digits, numbers only.
              </p>
            )}
          </div>
        </div>
        <div className="field">
          <label className="field-label">Packet Tracer file</label>
          <input type="file" accept=".pkt,.pka,.xml" onChange={onFile} />
          <p className="field-hint">
            The NPM is read from the file name (<span className="mono">H02_&#123;NPM&#125;</span>).
            Enter it manually if it is missing.
          </p>
        </div>
      </div>

      {file && (
        <div className="block">
          <div className="block-head">
            <div>
              <div className="block-title">
                <span className="step-num" aria-hidden="true">2</span>
                Subnet order
                <span className="tooltip-wrap">
                  <button
                    type="button"
                    className="tooltip-trigger"
                    aria-label="How to choose the subnet order"
                    aria-describedby="order-tip"
                    onKeyDown={(e) => { if (e.key === "Escape") e.currentTarget.blur(); }}
                  >
                    ?
                  </button>
                  <span id="order-tip" role="tooltip" className="tooltip-bubble">
                    <span className="tooltip-p">
                      Larger blocks are always allocated first. This choice only changes the
                      order of subnets that need the same mask.
                    </span>
                    <span className="tooltip-list">
                      <span>
                        <b>Host needs, largest first</b>: use this when the student ordered
                        those subnets by how many hosts they need.
                      </span>
                      <span>
                        <b>Subnet code, Z to A</b>: use this when the student ordered them by
                        their code, from Z to A.
                      </span>
                    </span>
                    <span className="tooltip-p">
                      Look at the student's plan first, then pick the order they used.
                    </span>
                  </span>
                </span>
              </div>
              <p className="block-sub">
                This choice only affects subnets that need the same mask. Larger blocks are always
                allocated first. Review the student's plan before choosing.
              </p>
            </div>
          </div>
          <div className="order-field">
            <p className="field-hint">
              File: <span className="mono">{file.name}</span>
            </p>
            <div className="radio-stack" role="radiogroup" aria-label="Subnet order for equal-size subnets">
              {ORDER_OPTIONS.map((o) => (
                <label className="radio" key={o.value}>
                  <input
                    type="radio"
                    name="allocation-order"
                    value={o.value}
                    checked={allocationOrder === o.value}
                    onChange={() => onOrder(o.value)}
                    disabled={busy}
                  />
                  <span>
                    <span className="radio-title">{o.title}</span>
                    <span className="radio-sub">{o.sub}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      <>
        <button
          className="btn primary btn-block"
          onClick={run}
          disabled={busy}
          aria-busy={busy}
        >
          {busy ? "Grading…" : "Grade submission"}
        </button>
        {busy && (
          <>
            <div
              className="run-progress"
              role="progressbar"
              aria-valuenow={stage}
              aria-valuemin={0}
              aria-valuemax={STAGE_LABELS.length}
              aria-label="Grading progress"
            >
              <div
                className="run-fill"
                style={{ width: `${(stage / STAGE_LABELS.length) * 100}%` }}
              />
            </div>
            <p className="run-stage">{STAGE_LABELS[Math.max(0, stage - 1)]}</p>
          </>
        )}
      </>

      {(solve || report) && (
        <div className="results-head">
          <span className="step-num" aria-hidden="true">3</span>
          <div>
            <div className="block-title">Results</div>
            <p className="block-sub">The expected addressing table first, then the grading report.</p>
          </div>
        </div>
      )}

      {solve && (
        <section className="block result-block" aria-label="Expected addressing">
          <div className="block-head">
            <div>
              <div className="block-title">Expected addressing</div>
              <p className="block-sub">The answer key this submission is graded against.</p>
            </div>
            <div className="block-actions">
              <span className="badge neutral">NPM {solve.npm}</span>
            </div>
          </div>
          <div className="facts">
            <div className="fact">
              <span className="fact-k">Variables</span>
              <span className="fact-v mono">
                {Object.entries(solve.resolved_vars).map(([k, v]) => `${k}=${v}`).join(", ") || "none"}
              </span>
            </div>
            <div className="fact">
              <span className="fact-k">Addresses used</span>
              <span className="fact-v mono">{solve.total_addresses_used}</span>
            </div>
            <div className="fact">
              <span className="fact-k">Fits base block</span>
              <span className={`badge ${solve.fits_base_block ? "pass" : "fail"}`}>
                <span className="dot" />
                {solve.fits_base_block ? "Yes" : "No"}
              </span>
            </div>
            <div className="fact">
              <span className="fact-k">Subnet order</span>
              <span className="fact-v">{ORDER_TITLES[orderValue] ?? solve.allocation_order}</span>
            </div>
          </div>
          <ExpectedTable subnets={solve.subnets} />
        </section>
      )}

      {report && <GradeReportView report={report} />}

      {solve && <PrefixRecommendation solve={solve} />}
    </div>
  );
}
