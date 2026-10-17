import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

export type ToastKind = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
  items?: string[];
}

/**
 * Toasts are raised from anywhere (including non-component code) and rendered
 * once, in a fixed corner. Every message type auto-clears after a set time;
 * hovering or focusing a toast holds it open so it can be read.
 */
const LIFETIME_MS: Record<ToastKind, number> = {
  success: 4000,
  info: 5000,
  warning: 7000,
  error: 8000,
};

const TITLES: Record<ToastKind, string> = {
  success: "Success!",
  error: "Error!",
  info: "Info!",
  warning: "Warning!",
};

const MAX_TOASTS = 4;
const EXIT_MS = 190;

let toasts: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot() {
  return toasts;
}

export function toast(kind: ToastKind, message: string, items?: string[]): void {
  const entry: ToastItem = { id: nextId++, kind, message, items };
  toasts = [...toasts, entry].slice(-MAX_TOASTS);
  notify();
}

export function dismissToast(id: number): void {
  if (!toasts.some((t) => t.id === id)) return;
  toasts = toasts.filter((t) => t.id !== id);
  notify();
}

function useToasts(): ToastItem[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

function ToastIcon({ kind }: { kind: ToastKind }) {
  const common = {
    width: 28,
    height: 28,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="9" />
      {kind === "success" && <path d="M8.2 12.3l2.6 2.6 5-5.4" />}
      {kind === "error" && <path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6" />}
      {kind === "info" && (
        <>
          <path d="M12 11.2v5" />
          <circle cx="12" cy="8" r="1" fill="currentColor" stroke="none" />
        </>
      )}
      {kind === "warning" && (
        <>
          <path d="M12 7.6v5.2" />
          <circle cx="12" cy="16.2" r="1" fill="currentColor" stroke="none" />
        </>
      )}
    </svg>
  );
}

function ToastCard({ item }: { item: ToastItem }) {
  const [held, setHeld] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const closing = useRef(false);

  // Animate out before the entry is dropped from the stack.
  const close = useCallback(() => {
    if (closing.current) return;
    closing.current = true;
    setLeaving(true);
    window.setTimeout(() => dismissToast(item.id), EXIT_MS);
  }, [item.id]);

  useEffect(() => {
    if (held || leaving) return;
    const timer = window.setTimeout(close, LIFETIME_MS[item.kind]);
    return () => window.clearTimeout(timer);
  }, [held, leaving, close, item.kind]);

  return (
    <div
      className={`toast ${item.kind}${leaving ? " leaving" : ""}`}
      role={item.kind === "error" || item.kind === "warning" ? "alert" : "status"}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
    >
      <span className="toast-ico">
        <ToastIcon kind={item.kind} />
      </span>
      <div className="toast-body">
        <div className="toast-title">{TITLES[item.kind]}</div>
        <div className="toast-msg">{item.message}</div>
        {item.items && item.items.length > 0 && (
          <ul className="toast-list">
            {item.items.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        )}
      </div>
      <button
        type="button"
        className="toast-close"
        onClick={close}
        aria-label="Dismiss message"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastHost() {
  const toasts = useToasts();
  return (
    <div className="toast-region" role="region" aria-label="Messages">
      {toasts.map((t) => (
        <ToastCard key={t.id} item={t} />
      ))}
    </div>
  );
}
