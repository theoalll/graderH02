import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { CaseSchema, DeviceType, EndDeviceSpec, SubnetDef, Variable } from "../types";
import { DeviceTypeManager } from "../components/DeviceTypeManager";
import { toast } from "../toast";

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

const deviceWord = (n: number) => (n === 1 ? "device" : "devices");
const LEAVE_MS = 220;

export function CaseBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState<CaseSchema>(emptyCase());
  const [deviceTypes, setDeviceTypes] = useState<DeviceType[]>([]);
  const [showTypes, setShowTypes] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});
  // Rows and cards animate out before they are removed from the list.
  const [leaveVar, setLeaveVar] = useState<number | null>(null);
  const [leaveSub, setLeaveSub] = useState<number | null>(null);
  const [leaveDev, setLeaveDev] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getCase(id).then(setC).catch((e) => toast("error", e.message));
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
  const delVar = (i: number) => {
    if (leaveVar !== null) return;
    setLeaveVar(i);
    window.setTimeout(() => {
      setC((prev) => ({ ...prev, variables: prev.variables.filter((_, j) => j !== i) }));
      setLeaveVar(null);
    }, LEAVE_MS);
  };

  // subnets
  const setSub = (i: number, patch: Partial<SubnetDef>) => {
    const subnets = c.subnets.map((s, j) => (j === i ? { ...s, ...patch } : s));
    update({ subnets });
  };
  const addSub = () =>
    update({
      subnets: [...c.subnets, { name: "", end_devices: [], wireless_to: null }],
    });
  const delSub = (i: number) => {
    if (leaveSub !== null) return;
    setLeaveSub(i);
    window.setTimeout(() => {
      setC((prev) => ({ ...prev, subnets: prev.subnets.filter((_, j) => j !== i) }));
      setLeaveSub(null);
      setCollapsed({});
    }, LEAVE_MS);
  };
  const toggleSub = (i: number) =>
    setCollapsed((prev) => ({ ...prev, [i]: !prev[i] }));
  const allCollapsed = c.subnets.length > 0 && c.subnets.every((_, i) => collapsed[i]);
  const setAllCollapsed = (v: boolean) =>
    setCollapsed(Object.fromEntries(c.subnets.map((_, i) => [i, v])));

  // expected devices (type, count, name, dhcp)
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
      end_devices: [
        ...c.subnets[si].end_devices,
        { type: "", count: "0", name: "", dhcp: true, exclude_from_grading: false },
      ],
    });
  const delEnd = (si: number, di: number) => {
    const key = `${si}-${di}`;
    if (leaveDev !== null) return;
    setLeaveDev(key);
    window.setTimeout(() => {
      setC((prev) => ({
        ...prev,
        subnets: prev.subnets.map((s, j) =>
          j === si ? { ...s, end_devices: s.end_devices.filter((_, k) => k !== di) } : s
        ),
      }));
      setLeaveDev(null);
    }, LEAVE_MS);
  };

  const save = async () => {
    const errs = validateCase(c);
    if (errs.length) {
      toast("error", "This case cannot be saved yet.", errs);
      return;
    }
    try {
      if (id) await api.updateCase(id, c);
      else await api.createCase(c);
      toast("success", "Case saved.");
      navigate("/cases");
    } catch (e) {
      toast("error", e instanceof ApiError ? e.message : "Save failed");
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2 className="page-title">{id ? "Edit case" : "New case"}</h2>
          <p className="page-sub">
            Define the lab, its variables, and the address allocation students must reach.
          </p>
        </div>
      </div>

      <div className="block">
        <div className="block-head">
          <div>
            <div className="block-title">Case setup</div>
            <p className="block-sub">The lab identity and the address block every subnet is carved from.</p>
          </div>
        </div>
        <div className="field-grid">
          <div className="field">
            <label className="field-label">Case title</label>
            <input
              value={c.title}
              placeholder="e.g. [Gasal 26/27] Building A"
              onChange={(e) => update({ title: e.target.value })}
            />
          </div>
          <div className="field">
            <label className="field-label">Allocation method</label>
            <select value={c.method} onChange={(e) => update({ method: e.target.value })}>
              <option value="VLSM">VLSM</option>
              <option value="FLSM">FLSM</option>
            </select>
            <p className="field-hint">
              VLSM uses variable-size blocks. FLSM uses one equal block size for every subnet.
            </p>
          </div>
        </div>
        <div className="field">
          <label className="field-label">Base block</label>
          <input
            className="mono-input"
            value={c.base_block}
            onChange={(e) => update({ base_block: e.target.value })}
            placeholder="e.g. 10.X.64.0/20"
          />
          <p className="field-hint">
            Variables defined below can be referenced here, e.g.{" "}
            <span className="mono">10.X.124.0/21</span>.
          </p>
        </div>
        <label className="inline">
          <input
            type="checkbox"
            checked={c.gateway_is_first_host}
            onChange={(e) => update({ gateway_is_first_host: e.target.checked })}
          />
          The gateway is the first usable host
        </label>
        <p className="field-hint">
          Turn this on when the lab expects the gateway to take the first usable address.
        </p>
      </div>

      <div className="block">
        <div className="block-head">
          <div>
            <div className="block-title">
              Variables{c.variables.length > 0 && ` (${c.variables.length})`}
            </div>
            <p className="block-sub">
              Values resolved from the student NPM, then substituted into the base block and device counts.
            </p>
          </div>
          <div className="block-actions">
            <button className="btn sm secondary" onClick={addVar}>
              Add variable
            </button>
          </div>
        </div>
        <div className="stack">
          {c.variables.map((v, i) => (
            <div className={`item-row${leaveVar === i ? " leaving" : ""}`} key={i} title="A variable resolves from the student NPM or from an expression over other variables.">
              <div className="grow">
                <input
                  className="mono-input"
                  placeholder="name (e.g. X)"
                  aria-label={`Variable ${i + 1} name`}
                  value={v.name}
                  onChange={(e) => setVar(i, { name: e.target.value })}
                />
              </div>
              <select
                className="var-source"
                value={v.source ?? ""}
                aria-label={`Variable ${i + 1} source`}
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
                  className="var-value"
                  placeholder="value"
                  aria-label={`Variable ${i + 1} value`}
                  value={v.value ?? 0}
                  onChange={(e) => setVar(i, { value: Number(e.target.value) })}
                />
              )}
              {v.source === "expr" && (
                <input
                  className="grow mono-input var-expr"
                  placeholder="expr e.g. NPM3 % 256"
                  aria-label={`Variable ${i + 1} expression`}
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
        <p className="field-hint">
          <span className="mono">npm_last2</span> takes the last two digits of the NPM,{" "}
          <span className="mono">npm_last3</span> the last three.{" "}
          <span className="mono">expr</span> computes a value from other variables, e.g.{" "}
          <span className="mono">X = NPM3 % 256</span>.
        </p>
      </div>

      <div className="block">
        <div className="block-head">
          <div>
            <div className="block-title">
              Subnets{c.subnets.length > 0 && ` (${c.subnets.length})`}
            </div>
            <p className="block-sub">
              Each subnet is a code plus the devices the student must place there.
            </p>
          </div>
          <div className="block-actions">
            {c.subnets.length > 1 && (
              <button className="btn sm ghost" onClick={() => setAllCollapsed(!allCollapsed)}>
                {allCollapsed ? "Expand all" : "Collapse all"}
              </button>
            )}
            <button className="btn sm secondary" onClick={() => setShowTypes(true)}>
              Device types
            </button>
            <button className="btn sm secondary" onClick={addSub}>
              Add subnet
            </button>
          </div>
        </div>

        {c.subnets.map((s, si) => {
          const isCollapsed = !!collapsed[si];
          const devCount = s.end_devices.length;
          const title = s.name.trim() || `Subnet ${si + 1}`;
          const nameId = `subnet-name-${si}`;
          return (
            <div className={`subnet-block${leaveSub === si ? " leaving" : ""}`} key={si}>
              <div className="subnet-head">
                <span className="subnet-eyebrow">Subnet {si + 1}</span>
                <div className="subnet-actions">
                  <button
                    className="btn sm ghost"
                    onClick={() => toggleSub(si)}
                    aria-expanded={!isCollapsed}
                  >
                    {isCollapsed
                      ? `Show ${devCount} ${deviceWord(devCount)}`
                      : `Hide ${deviceWord(devCount)}`}
                  </button>
                  <button className="btn sm danger" onClick={() => delSub(si)}>
                    Delete subnet
                  </button>
                </div>
              </div>

              <div className="field">
                <label className="field-label" htmlFor={nameId}>Subnet code</label>
                <input
                  id={nameId}
                  className="mono-input"
                  placeholder="e.g. CC-MON"
                  value={s.name}
                  onChange={(e) => setSub(si, { name: e.target.value })}
                />
                <p className="field-hint">
                  The code shown in the answer key and used by the subnet order option.
                </p>
              </div>

              <div
                className={`disclosure${!isCollapsed ? " open" : ""}`}
                aria-hidden={isCollapsed}
              >
                <div>
                  <div className="group-head">
                    <div>
                      <div className="group-title">
                        Expected devices{devCount > 0 ? ` (${devCount})` : ""}
                      </div>
                      <p className="group-sub">
                        Each device is graded 5 points for name, DHCP, IP range, mask, and
                        gateway, except devices with no IP on this subnet. The count sets the
                        size of this subnet.
                      </p>
                    </div>
                    <button className="btn sm secondary" onClick={() => addEnd(si)}>
                      Add device
                    </button>
                  </div>

                  {devCount === 0 && (
                    <div className="empty">
                      No devices in this subnet yet. Add at least one expected device.
                    </div>
                  )}

                  {s.end_devices.map((d, di) => {
                    const idBase = `sub-${si}-dev-${di}`;
                    return (
                      <div className={`dev-card${leaveDev === `${si}-${di}` ? " leaving" : ""}`} key={di}>
                        <div className="dev-card-head">
                          <span className="dev-card-title">Device {di + 1}</span>
                          <button
                            className="btn sm icon danger"
                            onClick={() => delEnd(si, di)}
                            aria-label={`Remove device ${di + 1} from ${title}`}
                            title="Remove device"
                          >
                            ✕
                          </button>
                        </div>
                        <div className="dev-fields">
                          <div className="field">
                            <label className="field-label" htmlFor={`${idBase}-type`}>Device type</label>
                            <select
                              id={`${idBase}-type`}
                              value={d.type}
                              onChange={(e) => setEnd(si, di, { type: e.target.value })}
                            >
                              <option value="">Choose a type</option>
                              {deviceTypes.map((t) => (
                                <option key={t.code} value={t.label}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                            <p className="field-hint">Sets how large this subnet must be.</p>
                          </div>
                          <div className="field">
                            <label className="field-label" htmlFor={`${idBase}-count`}>Count</label>
                            <input
                              id={`${idBase}-count`}
                              className="mono-input"
                              placeholder="e.g. 500 + (NPM3 % 35)"
                              value={d.count}
                              onChange={(e) => setEnd(si, di, { count: e.target.value })}
                            />
                            <p className="field-hint">Number of this type, as an expression.</p>
                          </div>
                          <div className="field span-2">
                            <label className="field-label" htmlFor={`${idBase}-name`}>Device name</label>
                            <input
                              id={`${idBase}-name`}
                              className="mono-input"
                              placeholder="e.g. PC WN"
                              value={d.name}
                              onChange={(e) => setEnd(si, di, { name: e.target.value })}
                            />
                            <p className="field-hint">The name checked in the student's file.</p>
                          </div>
                          <label className="check-inline span-2">
                            <input
                              type="checkbox"
                              checked={d.dhcp}
                              onChange={(e) => setEnd(si, di, { dhcp: e.target.checked })}
                            />
                            Obtains its address over DHCP
                          </label>
                          <label className="check-inline span-2">
                            <input
                              type="checkbox"
                              checked={!!d.exclude_from_grading}
                              onChange={(e) =>
                                setEnd(si, di, { exclude_from_grading: e.target.checked })
                              }
                            />
                            Not graded by IP
                          </label>
                          {d.exclude_from_grading && (
                            <p className="field-hint span-2">
                              Use this when the device has no address on this subnet's plan,
                              such as a device behind a home gateway or a layer 2 access point.
                              It still counts toward this subnet's size.
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
        {c.subnets.length === 0 && (
          <div className="empty">
            No subnets yet. Add the first subnet to define the expected allocation.
          </div>
        )}
        {c.subnets.length > 0 && (
          <button className="btn secondary" onClick={addSub}>
            Add subnet
          </button>
        )}
      </div>

      <div className="builder-actions">
        <button className="btn ghost" onClick={() => navigate("/cases")}>
          Cancel
        </button>
        <button className="btn primary" onClick={save}>
          Save case
        </button>
      </div>

      {showTypes && <DeviceTypeManager onClose={() => {
        setShowTypes(false);
        api.listDeviceTypes().then(setDeviceTypes).catch(() => {});
      }} />}
    </div>
  );
}
