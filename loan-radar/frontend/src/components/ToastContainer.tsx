import { useCallback, useEffect, useState } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export type Toast = {
  id: number;
  type: ToastType;
  title: string;
  message?: string;
  exiting?: boolean;
};

type AddToastFn = (type: ToastType, title: string, message?: string) => void;

let _nextId = 0;
let _addToast: AddToastFn | null = null;

export function showToast(type: ToastType, title: string, message?: string) {
  if (_addToast) {
    _addToast(type, title, message);
  }
}

const TOAST_ICONS: Record<ToastType, string> = {
  success: "✓",
  error: "✕",
  warning: "⚠",
  info: "ℹ",
};

const AUTO_DISMISS_MS = 5000;

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback<AddToastFn>((type, title, message) => {
    const id = ++_nextId;
    setToasts((prev) => [...prev, { id, type, title, message }]);
  }, []);

  useEffect(() => {
    _addToast = addToast;
    return () => {
      _addToast = null;
    };
  }, [addToast]);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)),
    );
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 250);
  }, []);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => dismissToast(t.id), AUTO_DISMISS_MS),
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts, dismissToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}${toast.exiting ? " toast-exit" : ""}`}
        >
          <span className="toast-icon">{TOAST_ICONS[toast.type]}</span>
          <div className="toast-body">
            <div className="toast-title">{toast.title}</div>
            {toast.message ? (
              <div className="toast-message">{toast.message}</div>
            ) : null}
          </div>
          <button
            className="toast-close"
            type="button"
            onClick={() => dismissToast(toast.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
