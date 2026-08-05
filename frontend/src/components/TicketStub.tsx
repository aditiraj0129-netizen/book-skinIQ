import type { ReactNode } from "react";
import clsx from "clsx";

interface TicketStubProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  stamp: ReactNode; // the "when" side — date/time/code
  meta?: ReactNode;
  accent?: "brass" | "sage" | "rust" | "ink";
  dark?: boolean;
  className?: string;
  onClick?: () => void;
}

const ACCENT_TEXT: Record<string, string> = {
  brass: "text-brass",
  sage: "text-sage",
  rust: "text-rust",
  ink: "text-ink",
};

const ACCENT_DOT: Record<string, string> = {
  brass: "bg-brass",
  sage: "bg-sage",
  rust: "bg-rust",
  ink: "bg-ink",
};

/**
 * The signature visual element of Bright Studio: every appointment is a
 * ticket stub, split by a perforated line into "what" (service) and "when"
 * (date/time). Used for service selection, chat booking confirmations, and
 * admin appointment rows — one motif, three contexts.
 */
export function TicketStub({
  eyebrow,
  title,
  subtitle,
  stamp,
  meta,
  accent = "brass",
  dark = false,
  className,
  onClick,
}: TicketStubProps) {
  const Wrapper = onClick ? "button" : "div";
  return (
    <Wrapper
      onClick={onClick}
      className={clsx(
        "group relative flex w-full flex-col overflow-hidden rounded-2xl border text-left shadow-sm transition-all",
        dark
          ? "border-ink-soft bg-ink text-linen"
          : "border-linen-soft bg-paper text-ink",
        onClick && "cursor-pointer hover:-translate-y-0.5 hover:shadow-lg",
        className
      )}
    >
      <div className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          {eyebrow && (
            <div className="flex items-center gap-2 mb-1.5">
              <span className={clsx("h-1.5 w-1.5 rounded-full", ACCENT_DOT[accent])} />
              <span
                className={clsx(
                  "font-mono text-[11px] uppercase tracking-widest",
                  dark ? "text-linen/60" : "text-ink/50"
                )}
              >
                {eyebrow}
              </span>
            </div>
          )}
          <h3 className="font-display text-xl font-medium leading-tight truncate">{title}</h3>
          {subtitle && (
            <p className={clsx("mt-1 text-sm leading-snug", dark ? "text-linen/70" : "text-ink/60")}>
              {subtitle}
            </p>
          )}
        </div>
        {meta && <div className="shrink-0">{meta}</div>}
      </div>

      <div className={clsx("ticket-perforation", dark && "ticket-perforation-dark")} />

      <div className={clsx("px-5 py-4 font-mono text-sm", ACCENT_TEXT[accent])}>{stamp}</div>
    </Wrapper>
  );
}
