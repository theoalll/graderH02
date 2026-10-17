import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { DeviceType } from "../types";
import { toast } from "../toast";

export function DeviceTypeManager({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<DeviceType[]>([]);
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [pendingDel, setPendingDel] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [delLeaving, setDelLeaving] = useState(false);
  const closing = useRef(false);
  const delClosing = useRef(false);

  // Play the exit animation before a dialog is removed from the tree.
  const requestClose = useCallback(() => {
    if (closing.current) return;
    closing.current = true;
    setLeaving(true);
    window.setTimeout(() => {
      setLeaving(false);
      closing.current = false;
      onClose();
    }, 220);
  }, [onClose]);

  const closeDel = useCallback(() => {
    if (delClosing.current) return;
    delClosing.current = true;
    setDelLeaving(true);
    window.setTimeout(() => {
      setPendingDel(null);
      setDelLeaving(false);
      delClosing.current = false;
    }, 220);
  }, []);

  const load = () =>
    api
      .listDeviceTypes()
      .then(setItems)
      .catch((e) =>
        toast("error", e instanceof ApiError ? e.message : "Could not load device types")
      );

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (pendingDel) closeDel();
      else requestClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingDel, closeDel, requestClose]);

  const slug = (s: string) => s.trim().toLowerCase().replace(/\s+/g, "_");

  const resetForm = () => {
    setEditing(null);
    setCode("");
    setLabel("");
  };

  const save = async () => {
    const c = slug(code);
    if (!c || !label.trim()) {
      toast("error", "Both code and label are required.");
      return;
    }
    try {
      if (editing) {
        await api.updateDeviceType(editing, { code: editing, label: label.trim() });
      } else {
        await api.createDeviceType({ code: c, label: label.trim() });
      }
      resetForm();
      load();
    } catch (e) {
      toast("error", e instanceof ApiError ? e.message : "Save failed");
    }
  };

  const remove = (c: string) => setPendingDel(c);

  const confirmDelete = async () => {
    if (!pendingDel) return;
    try {
      await api.deleteDeviceType(pendingDel);
      toast("info", `Device type "${pendingDel}" was deleted.`);
      closeDel();
      load();
    } catch (e) {
      toast("error", e instanceof ApiError ? e.message : "Delete failed");
      closeDel();
    }
  };

  const startEdit = (d: DeviceType) => {
    setEditing(d.code);
    setCode(d.code);
    setLabel(d.label);
  };

  return (
    <>
      <div className={`modal-backdrop${leaving ? " leaving" : ""}`} onClick={requestClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Manage device types" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 className="modal-title">Device types</h3>
          <button className="btn icon ghost" onClick={requestClose} aria-label="Close">✕</button>
        </div>
        <p className="muted meta-line">
          These types appear in the device-type list when authoring a case.
        </p>

        <div className="dtm-panel">
          <div className="dtm-panel-head">
            <div className="dtm-panel-title">
              Types{items.length > 0 ? ` (${items.length})` : ""}
            </div>
          </div>
          <div className="dtm-list">
            {items.map((d) => (
              <div className="dtm-row" key={d.code}>
                <div>
                  <div className="dtm-item-title">{d.label}</div>
                  <div className="faint dtm-item-code">
                    code: <span className="mono">{d.code}</span>
                  </div>
                </div>
                <div className="dtm-item-actions">
                  <button className="btn sm secondary" onClick={() => startEdit(d)}>Edit</button>
                  <button className="btn sm danger" onClick={() => remove(d.code)}>Delete</button>
                </div>
              </div>
            ))}
            {items.length === 0 && (
              <div className="muted">No device types yet. Add the first one below.</div>
            )}
          </div>
        </div>

        <div className="dtm-panel">
          <div className="dtm-panel-head">
            <div className="dtm-panel-title">
              {editing ? `Edit "${editing}"` : "Add a device type"}
            </div>
          </div>
          <div className="dtm-form-grid">
            <div className="field">
              <label className="field-label" htmlFor="dtm-code">Code</label>
              <input
                id="dtm-code"
                className="mono-input"
                value={code}
                disabled={!!editing}
                placeholder="e.g. pc"
                onChange={(e) => setCode(e.target.value)}
              />
              <p className="field-hint">Short lowercase key. Cannot change once saved.</p>
            </div>
            <div className="field">
              <label className="field-label" htmlFor="dtm-label">Label</label>
              <input
                id="dtm-label"
                value={label}
                placeholder="e.g. PC"
                onChange={(e) => setLabel(e.target.value)}
              />
              <p className="field-hint">Shown in the device-type list.</p>
            </div>
          </div>
          <div className="form-row-end">
            {editing && (
              <button className="btn ghost" onClick={resetForm}>
                Cancel
              </button>
            )}
            <button className="btn primary" onClick={save}>
              {editing ? "Save changes" : "Add device type"}
            </button>
          </div>
        </div>
      </div>
    </div>

      {pendingDel && (
        <div className={`modal-backdrop${delLeaving ? " leaving" : ""}`} onClick={closeDel}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Confirm delete device type" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 className="modal-title">Delete device type</h3>
              <button className="btn icon ghost" onClick={closeDel} aria-label="Close">✕</button>
            </div>
            <p className="muted flush-top">
              Delete device type <b>{pendingDel}</b>? This cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="btn ghost" onClick={closeDel}>Cancel</button>
              <button className="btn danger" onClick={confirmDelete}>Delete type</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
