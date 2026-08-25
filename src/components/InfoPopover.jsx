import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "./InfoPopover.css";

export default function InfoPopover({ label, title, actionLabel, children }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left: 16, top: 80 });
  const buttonRef = useRef(null);
  const contentRef = useRef(null);
  const contentId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const place = () => {
      const trigger = buttonRef.current?.getBoundingClientRect();
      const panel = contentRef.current?.getBoundingClientRect();
      if (!trigger || !panel) return;
      const margin = 12;
      const left = Math.min(window.innerWidth - panel.width - margin, Math.max(margin, trigger.left));
      const below = trigger.bottom + 9;
      const top = below + panel.height <= window.innerHeight - margin ? below : Math.max(margin, trigger.top - panel.height - 9);
      setPosition({ left, top });
    };
    const closeOnOutside = (event) => {
      if (!buttonRef.current?.contains(event.target) && !contentRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event) => { if (event.key === "Escape") { setOpen(false); buttonRef.current?.focus(); } };
    const frame = requestAnimationFrame(place);
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);
  return (
    <span className="info-popover">
      <button ref={buttonRef} className={actionLabel ? "info-popover-action" : ""} type="button" aria-label={label} aria-expanded={open} aria-controls={contentId} onClick={() => setOpen((value) => !value)}><b aria-hidden="true">ⓘ</b>{actionLabel && <span>{actionLabel}</span>}</button>
      {open && createPortal(<span ref={contentRef} id={contentId} className="info-popover-content is-open" role="tooltip" style={position}>
        <strong>{title}</strong>{children}
      </span>, document.body)}
    </span>
  );
}
