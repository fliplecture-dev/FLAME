"use client";
import { useEffect, useId, useRef } from "react";
import { AlertTriangle } from "lucide-react";

export function RemovalConfirmation({ name, kind, context, onCancel, onConfirm }: {
  name: string; kind: "curriculum" | "subject"; context?: string; onCancel: () => void; onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      if (previous?.isConnected && !previous.hasAttribute("disabled")) previous.focus({ preventScroll: true });
      else {
        const openDialog = Array.from(document.querySelectorAll<HTMLDialogElement>("dialog[open]")).at(-1);
        const fallback = openDialog?.querySelector<HTMLElement>('button:not(:disabled), input') ?? document.querySelector<HTMLElement>('.desktop-sidebar button[aria-label="Add from Library"]');
        fallback?.focus({ preventScroll: true });
      }
    };
  }, []);
  return <dialog ref={dialog} className="removal-dialog" aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} onCancel={event => { event.preventDefault(); event.stopPropagation(); onCancel(); }} onKeyDown={event => {
    event.stopPropagation();
    if (event.key !== "Tab") return;
    const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button"));
    if (event.shiftKey && document.activeElement === buttons[0]) { event.preventDefault(); buttons.at(-1)?.focus(); }
    else if (!event.shiftKey && document.activeElement === buttons.at(-1)) { event.preventDefault(); buttons[0]?.focus(); }
  }}>
    <span className="removal-dialog-icon"><AlertTriangle size={22} aria-hidden="true" /></span>
    <h2 id={`${id}-title`}>Remove {name}?</h2>
    {context && <p className="removal-dialog-context">{context}</p>}
    <p id={`${id}-description`}>This {kind} will be removed from your learning view. Your progress and learning history will be preserved in this tab session.</p>
    <div className="removal-dialog-actions"><button autoFocus onClick={onCancel}>Cancel</button><button className="confirm-remove" onClick={onConfirm}>Remove</button></div>
  </dialog>;
}
