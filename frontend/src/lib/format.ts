export function formatPrice(price: number): string {
  return `$${price.toFixed(0)}`;
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} hr` : `${h}h ${m}m`;
}

export function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatDateTime(iso: string): string {
  return `${formatDateShort(iso)}, ${formatTime(iso)}`;
}

/** Short, ticket-style confirmation code derived from an appointment id. */
export function confirmationCode(appointmentId: string): string {
  return appointmentId.replace(/-/g, "").slice(0, 8).toUpperCase();
}

/** Builds a downloadable .ics calendar file for an appointment — the same
 * "add to calendar" convenience Calendly/Cal.com are known for. */
export function buildIcsFile(opts: {
  title: string;
  description: string;
  startIso: string;
  durationMinutes: number;
}): string {
  const start = new Date(opts.startIso);
  const end = new Date(start.getTime() + opts.durationMinutes * 60000);
  const fmt = (d: Date) =>
    d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Bright Studio//Booking Assistant//EN",
    "BEGIN:VEVENT",
    `UID:${crypto.randomUUID()}@brightstudio`,
    `DTSTAMP:${fmt(new Date())}`,
    `DTSTART:${fmt(start)}`,
    `DTEND:${fmt(end)}`,
    `SUMMARY:${opts.title}`,
    `DESCRIPTION:${opts.description}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
}

export function downloadIcs(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
