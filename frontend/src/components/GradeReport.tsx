import { useState } from "react";
import { GradeReport } from "../types";

const statusBadge = (c: { passed: boolean; fraction: number }) => {
  if (c.passed) return <span className="badge pass"><span className="dot" />PASS</span>;
  if (c.fraction > 0) return <span className="badge partial"><span className="dot" />PARTIAL</span>;
  return <span className="badge fail"><span className="dot" />FAIL</span>;
};

const subnetStatus = (sg: { checks: { passed: boolean; fraction: number }[] }) => {
  if (sg.checks.length > 0 && sg.checks.every((c) => c.passed))
    return <span className="badge pass"><span className="dot" />PASS</span>;
  if (sg.checks.some((c) => c.passed || c.fraction > 0))
    return <span className="badge partial"><span className="dot" />PARTIAL</span>;
  return <span className="badge fail"><span className="dot" />FAIL</span>;
};

export function GradeReportView({ report }: { report: GradeReport }) {
  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const sg of report.subnet_grades) {
      sg.device_grades.forEach((dg, di) => {
        if (di === 0) init[`${dg.name}|${dg.type}`] = true;
      });
    }
    return init;
  });

  const toggle = (key: string) => setOpen((prev) => ({ ...prev, [key]: !prev[key] }));

  const pct = report.auto_max ? Math.round((report.auto_score / report.auto_max) * 100) : 0;
  const orderShort =
    report.allocation_order === "code_desc" ? "Subnet code, Z to A" : "Host needs, largest first";

  return (
    <section className="block result-block" aria-label="Grading report">
      <div className="block-head">
        <div>
          <div className="block-title">Grading report</div>
          <p className="block-sub">
            Automatic checks first, then the expected devices.
          </p>
        </div>
        <div className="block-actions">
          <span className="badge neutral" title="Same-mask subnet order used for the answer key">
            {orderShort}
          </span>
          <span className="badge neutral">NPM {report.npm}</span>
        </div>
      </div>

      <div className="score-banner">
        <div className="score-main">
          <span className="val">{report.auto_score.toFixed(1)}</span>
          <span className="max">/ {report.auto_max.toFixed(0)} points</span>
          <span className="pct">{pct}%</span>
        </div>
        <div className="progress" role="img" aria-label={`Score ${pct} percent`}>
          <div className="fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <p className="muted meta-line">{report.summary}</p>

      {report.subnet_grades.map((sg) => (
        <div className="subnet-report" key={sg.name}>
          <div className="subnet-head">
            <span className="subnet-name mono">{sg.name}</span>
            <span className="subnet-side">
              {subnetStatus(sg)}
              <span className="subnet-score">
                {sg.score.toFixed(1)} / {sg.max_score.toFixed(0)}
              </span>
            </span>
          </div>
          <div className="scroll-x">
          <table className="checks">
            <thead>
              <tr>
                <th className="c-status">Status</th>
                <th>Check</th>
                <th className="mono">Expected</th>
                <th className="mono">Actual</th>
                <th className="c-score">Score</th>
              </tr>
            </thead>
            <tbody>
              {sg.checks.map((c) => (
                <tr key={c.key}>
                  <td className="c-status">{statusBadge(c)}</td>
                  <td>
                    <div className="c-label">{c.label}</div>
                    {c.detail && <div className="c-detail">{c.detail}</div>}
                  </td>
                  <td className="c-expected mono">{c.expected || ""}</td>
                  <td className="c-actual mono">{c.actual || ""}</td>
                  <td className="c-score">{c.score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          {sg.device_grades.length > 0 && (
            <div className="devices-block">
              <div className="devices-head">Expected devices (5 points each)</div>
              {sg.device_grades.map((dg) => {
                const key = `${dg.name}|${dg.type}`;
                const isOpen = !!open[key];
                return (
                  <div className="device-grade" key={key}>
                    <button
                      type="button"
                      className="device-head"
                      aria-expanded={isOpen}
                      aria-controls={`dev-${key}`}
                      onClick={() => toggle(key)}
                    >
                      <span className="device-name mono">{dg.name}</span>
                      {dg.type && <span className="device-type tag">{dg.type}</span>}
                      <span className="device-toggle">{isOpen ? "Hide checks" : "Show checks"}</span>
                      <span className={`badge ${dg.matched ? (dg.score >= 5 ? "pass" : dg.score > 0 ? "partial" : "fail") : "fail"}`}>
                        {dg.score.toFixed(0)} / {dg.max_score.toFixed(0)}
                      </span>
                      {!dg.matched && <span className="muted small">Not found</span>}
                    </button>
                    <div
                      id={`dev-${key}`}
                      className={`disclosure${isOpen ? " open" : ""}`}
                      aria-hidden={!isOpen}
                    >
                      <div>
                        <div className="scroll-x">
                          <table className="checks compact">
                            <tbody>
                              {dg.checks.map((c) => (
                                <tr key={c.key}>
                                  <td className="c-status">{statusBadge(c)}</td>
                                  <td><div className="c-label">{c.label}</div></td>
                                  <td className="c-expected mono">{c.expected || ""}</td>
                                  <td className="c-actual mono">{c.actual || ""}</td>
                                  <td className="c-score">{c.score.toFixed(0)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}

    </section>
  );
}
