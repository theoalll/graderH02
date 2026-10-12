import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { DeviceType } from "../types";

export function DeviceTypeManager({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<DeviceType[]>([]);
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [pendingDel, setPendingDel] = useState<string | null>(null);

  const load = () =>
    api
      .listDeviceTypes()
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed"));

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (pendingDel) setPendingDel(null);
      else onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingDel, onClose]);

  const slug = (s: string) => s.trim().toLowerCase().replace(/\s+/g, "_");

  const save = async () => {
    setError("");
    const c = slug(code);
    if (!c || !label.trim()) return setError("Code and label are required");
    try {
      if (editing) {
        await api.updateDeviceType(editing, { code: editing, label: label.trim() });
      } else {
        await api.createDeviceType({ code: c, label: label.trim() });
      }
      setCode("");
      setLabel("");
      setEditing(null);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed");
    }
  };

  const remove = (c: string) => setPendingDel(c);

  const confirmDelete = async () => {
    if (!pendingDel) return;
    try {
      await api.deleteDeviceType(pendingDel);
      setPendingDel(null);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Delete failed");
      setPendingDel(null);
    }
  };

  const startEdit = (d: DeviceType) => {
    setEditing(d.code);
    setCode(d.code);
    setLabel(d.label);
  };

  return (
    <>
      <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Manage device types" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ fontSize: 16 }}>Device Types</h3>
          <button className="btn icon ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
          Master list used for the device-type dropdown when authoring a case.
        </p>
        {error && <div className="alert error"><span className="alert-ico" /><span>{error}</span></div>}

        <div className="dtm-list">
          {items.map((d) => (
            <div className="dtm-row" key={d.code}>
              <div>
                <div style={{ fontWeight: 500 }}>{d.label}</div>
                <div className="faint" style={{ fontSize: 12 }}>
                  <span className="mono">{d.code}</span>
                </div>
              </div>
              <div className="row" style={{ gap: 6 }}>
                <button className="btn sm secondary" onClick={() => startEdit(d)}>Edit</button>
                <button className="btn sm danger" onClick={() => remove(d.code)}>Delete</button>
              </div>
            </div>
          ))}
          {items.length === 0 && <div className="muted">No device types yet.</div>}
        </div>

        <div className="divider" />

        <div className="eyebrow" style={{ marginBottom: 8 }}>
          {editing ? `Edit "${editing}"` : "Add device type"}
        </div>
        <div className="field-grid">
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Code</label>
            <input
              className="mono-input"
              value={code}
              disabled={!!editing}
              placeholder="e.g. pc"
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Label</label>
            <input value={label} placeholder="e.g. PC" onChange={(e) => setLabel(e.target.value)} />
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          {editing && (
            <button className="btn ghost" onClick={() => { setEditing(null); setCode(""); setLabel(""); }}>
              Cancel
            </button>
          )}
          <button className="btn primary" onClick={save}>
            {editing ? "Save" : "Add"}
          </button>
        </div>
      </div>
    </div>

      {pendingDel && (
        <div className="modal-backdrop" onClick={() => setPendingDel(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Confirm delete device type" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ fontSize: 16 }}>Delete device type</h3>
              <button className="btn icon ghost" onClick={() => setPendingDel(null)} aria-label="Close">✕</button>
            </div>
            <p className="muted" style={{ marginTop: 0 }}>
              Delete device type <b>{pendingDel}</b>? This action cannot be undone.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <button className="btn ghost" onClick={() => setPendingDel(null)}>Cancel</button>
              <button className="btn danger" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
