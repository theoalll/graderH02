import { GradeReport } from "../types";

const statusBadge = (c: { passed: boolean; fraction: number }) => {
  if (c.passed) return <span className="badge pass"><span className="dot" />PASS</span>;
  if (c.fraction > 0) return <span className="badge partial"><span className="dot" />PARTIAL</span>;
  return <span className="badge fail"><span className="dot" />FAIL</span>;
};

export function GradeReportView({ report }: { report: GradeReport }) {
  const pct = report.auto_max ? Math.round((report.auto_score / report.auto_max) * 100) : 0;
  return (
    <section className="section" style={{ marginTop: 28 }}>
      <div className="row-between" style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 16 }}>Grade Report</h3>
        <span className="badge neutral">NPM {report.npm}</span>
      </div>

      <div className="score-banner">
        <div className="score-main">
          <span className="val">{report.auto_score.toFixed(1)}</span>
          <span className="max">/ {report.auto_max.toFixed(0)} auto-graded</span>
          <span className="pct">{pct}%</span>
        </div>
        <div className="progress">
          <div className="fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>{report.summary}</p>

      {report.subnet_grades.map((sg) => (
        <div className="subnet-report" key={sg.name}>
          <div className="subnet-head">
            <span className="subnet-name mono">{sg.name}</span>
            <span className="subnet-score">
              {sg.score.toFixed(1)} / {sg.max_score.toFixed(0)}
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
              <div className="devices-head">End devices (5 pts each)</div>
              {sg.device_grades.map((dg) => (
                <div className="device-grade" key={dg.name + dg.type}>
                  <div className="device-head">
                    <span className="device-name mono">{dg.name}</span>
                    {dg.type && <span className="device-type tag">{dg.type}</span>}
                    <span className={`badge ${dg.matched ? (dg.score >= 5 ? "pass" : dg.score > 0 ? "partial" : "fail") : "fail"}`}>
                      {dg.score.toFixed(0)} / {dg.max_score.toFixed(0)}
                    </span>
                    {!dg.matched && <span className="muted small">not found</span>}
                  </div>
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
              ))}
            </div>
          )}
        </div>
      ))}

    </section>
  );
}

