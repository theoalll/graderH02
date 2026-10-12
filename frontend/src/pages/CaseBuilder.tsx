import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { CaseSchema, DeviceType, EndDeviceSpec, SubnetDef, Variable } from "../types";
import { DeviceTypeManager } from "../components/DeviceTypeManager";

const genId = (): string =>
  (globalThis as any).crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);

function validateCase(c: CaseSchema): string[] {
  const errors: string[] = [];
  if (!c.title.trim()) errors.push("Case title is required.");
  if (!c.base_block.trim()) errors.push("Base block is required.");
  if (c.subnets.length === 0) {
    errors.push("Add at least one subnet.");
    return errors;
  }
  c.subnets.forEach((s, si) => {
    const name = s.name.trim();
    const sLabel = name ? `"${name}"` : `Subnet #${si + 1}`;
    if (!name) errors.push(`Subnet #${si + 1}: name is required.`);
    if (s.end_devices.length === 0) {
      errors.push(`${sLabel}: add at least one expected device.`);
      return;
    }
    s.end_devices.forEach((d, di) => {
      const dName = d.name.trim();
      const dLabel = dName ? `"${dName}"` : `device #${di + 1}`;
      if (!d.type.trim()) errors.push(`${sLabel} / ${dLabel}: device type is required.`);
      const count = (d.count ?? "").trim();
      if (!count) {
        errors.push(`${sLabel} / ${dLabel}: count is required.`);
      } else if (/^\d+$/.test(count) && Number(count) <= 0) {
        errors.push(`${sLabel} / ${dLabel}: count must be greater than 0.`);
      }
      if (!dName) errors.push(`${sLabel} / ${dLabel}: device name is required.`);
    });
  });
  return errors;
}

const emptyCase = (): CaseSchema => ({
  case_id: genId(),
  title: "",
  base_block: "10.X.64.0/20",
  variables: [
    { name: "X", source: "npm_last2" },
    { name: "NPM3", source: "npm_last3" },
  ],
  subnets: [],
  method: "VLSM",
  order_tiebreak: "alpha",
  gateway_is_first_host: false,
  grading: {
    auto: ["dhcp_pool", "dhcp_mask", "dhcp_gateway", "gateway", "links_up"],
    manual: ["note_name_npm", "palette_boxes", "device_labels", "wireless_dots"],
  },
});

export function CaseBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState<CaseSchema>(emptyCase());
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const [msg, setMsg] = useState("");
  const [deviceTypes, setDeviceTypes] = useState<DeviceType[]>([]);
  const [showTypes, setShowTypes] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.getCase(id).then(setC).catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    api.listDeviceTypes().then(setDeviceTypes).catch(() => {});
  }, []);

  const update = (patch: Partial<CaseSchema>) => setC({ ...c, ...patch });

  // variables
  const setVar = (i: number, patch: Partial<Variable>) => {
    const variables = c.variables.map((v, j) => (j === i ? { ...v, ...patch } : v));
    update({ variables });
  };
  const addVar = () => update({ variables: [...c.variables, { name: "", source: "const", value: 0 }] });
  const delVar = (i: number) => update({ variables: c.variables.filter((_, j) => j !== i) });

  // subnets
  const setSub = (i: number, patch: Partial<SubnetDef>) => {
    const subnets = c.subnets.map((s, j) => (j === i ? { ...s, ...patch } : s));
    update({ subnets });
  };
  const addSub = () =>
    update({
      subnets: [...c.subnets, { name: "", end_devices: [], wireless_to: null }],
    });
  const delSub = (i: number) => update({ subnets: c.subnets.filter((_, j) => j !== i) });

  // expected end devices (single merged section: type, count, name, dhcp)
  const setEnd = (si: number, di: number, patch: Partial<EndDeviceSpec>) => {
    const subnets = c.subnets.map((s, j) => {
      if (j !== si) return s;
      const end_devices = s.end_devices.map((d, k) => (k === di ? { ...d, ...patch } : d));
      return { ...s, end_devices };
    });
    update({ subnets });
  };
  const addEnd = (si: number) =>
    setSub(si, {
      end_devices: [...c.subnets[si].end_devices, { type: "", count: "0", name: "", dhcp: true }],
    });
  const delEnd = (si: number, di: number) =>
    setSub(si, { end_devices: c.subnets[si].end_devices.filter((_, k) => k !== di) });

  const save = async () => {
    setError("");
    setFieldErrors([]);
    setMsg("");
    const errs = validateCase(c);
    if (errs.length) {
      setFieldErrors(errs);
      return;
    }
    try {
      if (id) await api.updateCase(id, c);
      else await api.createCase(c);
      setMsg("Saved.");
      navigate("/cases");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed");
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2 className="page-title">{id ? "Edit Case" : "New Case"}</h2>
          <p className="page-sub">Define the IP-addressing lab and its expected allocation.</p>
        </div>
      </div>

      {error && <div className="alert error"><span className="alert-ico" /><span>{error}</span></div>}
      {msg && <div className="alert ok"><span className="alert-ico" /><span>{msg}</span></div>}

      <div className="panel section">
        <div className="field-grid">
          <div className="field">
            <label className="field-label">Method</label>
            <select value={c.method} onChange={(e) => update({ method: e.target.value })}>
              <option value="VLSM">VLSM</option>
              <option value="FLSM">FLSM</option>
            </select>
            <p className="field-hint">VLSM = variable-length; FLSM = equal blocks.</p>
          </div>
        </div>
        <div className="field">
          <label className="field-label">Title</label>
          <input value={c.title} onChange={(e) => update({ title: e.target.value })} />
        </div>
        <div className="field">
          <label className="field-label">Base Block</label>
          <input
            className="mono-input"
            value={c.base_block}
            onChange={(e) => update({ base_block: e.target.value })}
            placeholder="e.g. 10.X.64.0/20"
          />
          <p className="field-hint">
            Use variable names from below, e.g. <span className="mono">10.X.124.0/21</span>.
          </p>
        </div>
        <label className="inline" style={{ marginTop: 4 }}>
          <input
            type="checkbox"
            checked={c.gateway_is_first_host}
            onChange={(e) => update({ gateway_is_first_host: e.target.checked })}
          />
          Gateway is the first usable host
        </label>
        <p className="field-hint">
          When on, the gateway IP equals the first host (per some lab conventions).
        </p>
      </div>

      <div className="section">
        <div className="row-between" style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 15 }}>Variables</h3>
        </div>
        <div className="stack">
          {c.variables.map((v, i) => (
            <div className="item-row" key={i} title="A variable resolves from the student NPM or from an expression over other variables.">
              <div className="grow">
                <input
                  className="mono-input"
                  placeholder="name (e.g. X)"
                  value={v.name}
                  onChange={(e) => setVar(i, { name: e.target.value })}
                />
              </div>
              <select
                style={{ maxWidth: 160 }}
                value={v.source ?? ""}
                onChange={(e) => setVar(i, { source: (e.target.value || null) as Variable["source"] })}
              >
                <option value="npm_last2">npm_last2</option>
                <option value="npm_last3">npm_last3</option>
                <option value="const">const</option>
                <option value="expr">expr</option>
              </select>
              {v.source === "const" && (
                <input
                  type="number"
                  style={{ maxWidth: 120 }}
                  placeholder="value"
                  value={v.value ?? 0}
                  onChange={(e) => setVar(i, { value: Number(e.target.value) })}
                />
              )}
              {v.source === "expr" && (
                <input
                  className="grow mono-input"
                  style={{ minWidth: 140 }}
                  placeholder="expr e.g. NPM3 % 256"
                  value={v.expr ?? ""}
                  onChange={(e) => setVar(i, { expr: e.target.value })}
                />
              )}
              <button className="btn icon danger" onClick={() => delVar(i)} aria-label="Remove variable">
                ✕
              </button>
            </div>
          ))}
        </div>
        <button className="btn sm secondary" style={{ marginTop: 12 }} onClick={addVar}>
          + Add variable
        </button>
        <p className="field-hint">
          <span className="mono">expr</span> computes a value from other variables (e.g.{" "}
          <span className="mono">X = NPM3 % 256</span>), instead of reading NPM digits directly.
        </p>
      </div>

      <div className="section">
        <div className="row-between" style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 15 }}>Subnets</h3>
          <button className="btn sm secondary" onClick={() => setShowTypes(true)}>
            Manage device types
          </button>
        </div>
        {c.subnets.map((s, si) => (
          <div className="subnet-block" key={si}>
            <div className="subnet-head">
              <div className="grow" style={{ flex: 1, minWidth: 160 }}>
                <input
                  className="mono-input"
                  placeholder="subnet name / code (e.g. CC-MON)"
                  value={s.name}
                  onChange={(e) => setSub(si, { name: e.target.value })}
                />
              </div>
              <button className="btn sm danger" onClick={() => delSub(si)}>
                Delete subnet
              </button>
            </div>

              <div className="subgroup">
                <div className="eyebrow row-between" style={{ marginBottom: 8 }}>
                  <span>Expected end devices <span className="muted small">(5 pts each: name, DHCP, IP range, mask, gateway)</span></span>
                </div>
                <div className="scroll-x">
                <div className="enddev-head">
                  <span>Type</span>
                  <span>Count (expr)</span>
                  <span>Device name</span>
                  <span>DHCP</span>
                  <span></span>
                </div>
                {s.end_devices.map((d, di) => (
                  <div className="dev-row enddev-row" key={di}>
                    <select
                      className="mono-input"
                      value={d.type}
                      onChange={(e) => setEnd(si, di, { type: e.target.value })}
                    >
                      <option value="">Type…</option>
                      {deviceTypes.map((t) => (
                        <option key={t.code} value={t.label}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                    <input
                      className="mono-input"
                      placeholder="e.g. 500 + (NPM3 % 35)"
                      value={d.count}
                      onChange={(e) => setEnd(si, di, { count: e.target.value })}
                    />
                    <input
                      className="mono-input"
                      placeholder="e.g. PC WN"
                      value={d.name}
                      onChange={(e) => setEnd(si, di, { name: e.target.value })}
                    />
                    <label className="check-inline" title="End device should be DHCP-configured">
                      <input
                        type="checkbox"
                        checked={d.dhcp}
                        onChange={(e) => setEnd(si, di, { dhcp: e.target.checked })}
                      />
                      DHCP
                    </label>
                    <button
                      className="btn icon danger"
                      onClick={() => delEnd(si, di)}
                      aria-label="Remove expected device"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                </div>
                <button className="btn sm secondary" onClick={() => addEnd(si)}>
                  + Add expected device
                </button>
              <p className="field-hint">
                Each row binds a <b>device type</b> (sizes the subnet), a <b>count</b> expression
                (number of devices of that type), a <b>device name</b> to verify, and a <b>DHCP</b> flag.
                The named device is graded 5 points; the count drives only the subnet size.
              </p>
            </div>
          </div>
        ))}
        <button className="btn secondary" style={{ marginTop: 4 }} onClick={addSub}>
          + Add subnet
        </button>
      </div>

      {fieldErrors.length > 0 && (
        <div className="alert error">
          <span className="alert-ico" />
          <div>
            <div>Fix the following before saving:</div>
            <ul style={{ margin: "4px 0 0 18px" }}>
              {fieldErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="builder-actions">
        <button className="btn ghost" onClick={() => navigate("/cases")}>
          Cancel
        </button>
        <button className="btn primary" onClick={save}>
          Save Case
        </button>
      </div>

      {showTypes && <DeviceTypeManager onClose={() => {
        setShowTypes(false);
        api.listDeviceTypes().then(setDeviceTypes).catch(() => {});
      }} />}
    </div>
  );
}
