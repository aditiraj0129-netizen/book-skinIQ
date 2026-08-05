import { useEffect, useMemo, useState } from "react";
import { CalendarPlus, Check, ChevronLeft, ChevronRight, Copy, Loader2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useUserAuth } from "../lib/userAuth";
import type { AvailabilitySlot, Service } from "../lib/types";
import {
  buildIcsFile,
  confirmationCode,
  downloadIcs,
  formatDuration,
  formatPrice,
} from "../lib/format";
import { TicketStub } from "./TicketStub";

function addDays(date: Date, days: number) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatSlotTime(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

interface Props {
  services: Service[];
  selectedServiceId?: string | null;
}

export function BookingCalendar({ services, selectedServiceId }: Props) {
  const { user } = useUserAuth();
  const [serviceId, setServiceId] = useState<string>(selectedServiceId || services[0]?.id || "");
  const [weekStart, setWeekStart] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState("");
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<{ id: string; start: string } | null>(null);

  useEffect(() => {
    if (selectedServiceId) setServiceId(selectedServiceId);
  }, [selectedServiceId]);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setEmail(user.email);
    }
  }, [user]);

  const service = services.find((s) => s.id === serviceId);

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  useEffect(() => {
    if (!service) return;
    setLoadingSlots(true);
    setSelectedSlot(null);
    api
      .getAvailability(service.id, isoDate(selectedDate))
      .then(setSlots)
      .catch(() => setSlots([]))
      .finally(() => setLoadingSlots(false));
  }, [service, selectedDate]);

  async function handleBook() {
    if (!service || !selectedSlot || !name.trim() || !email.trim()) return;
    setBooking(true);
    setError(null);
    try {
      const appt = await api.book({
        service_id: service.id,
        start_time: selectedSlot.start,
        customer_name: name.trim(),
        customer_email: email.trim(),
        customer_phone: phone.trim(),
      });
      setConfirmed({ id: appt.id, start: appt.start_time });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("That slot was just taken — please pick another time.");
        const fresh = await api.getAvailability(service.id, isoDate(selectedDate));
        setSlots(fresh);
        setSelectedSlot(null);
      } else {
        setError("Something went wrong — please try again.");
      }
    } finally {
      setBooking(false);
    }
  }

  if (confirmed && service) {
    return <BookingConfirmed service={service} startIso={confirmed.start} onReset={() => setConfirmed(null)} />;
  }

  return (
    <div className="rounded-3xl border border-linen-soft bg-paper p-6 shadow-sm sm:p-8">
      {/* Service tabs */}
      <div className="mb-6 flex flex-wrap gap-2">
        {services.map((s) => (
          <button
            key={s.id}
            onClick={() => setServiceId(s.id)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              s.id === serviceId ? "bg-ink text-linen" : "border border-linen-soft text-ink/60 hover:bg-linen-soft"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>

      {service && (
        <p className="mb-6 font-mono text-sm text-ink/50">
          {formatDuration(service.duration_minutes)} · {formatPrice(service.price)}
        </p>
      )}

      {/* Week strip */}
      <div className="mb-5 flex items-center gap-2">
        <button
          onClick={() => setWeekStart((d) => addDays(d, -7))}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-linen-soft text-ink/50 hover:bg-linen-soft"
          aria-label="Previous week"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="grid flex-1 grid-cols-7 gap-1.5">
          {days.map((d) => {
            const active = isoDate(d) === isoDate(selectedDate);
            const isPast = isoDate(d) < isoDate(new Date());
            return (
              <button
                key={d.toISOString()}
                disabled={isPast}
                onClick={() => setSelectedDate(d)}
                className={`flex flex-col items-center rounded-xl py-2 text-xs transition disabled:opacity-30 ${
                  active ? "bg-ink text-linen" : "hover:bg-linen-soft text-ink/70"
                }`}
              >
                <span className="font-mono uppercase tracking-wide">
                  {d.toLocaleDateString(undefined, { weekday: "short" })}
                </span>
                <span className="mt-0.5 font-display text-base font-medium">{d.getDate()}</span>
              </button>
            );
          })}
        </div>
        <button
          onClick={() => setWeekStart((d) => addDays(d, 7))}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-linen-soft text-ink/50 hover:bg-linen-soft"
          aria-label="Next week"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Slot grid */}
      <div className="mb-6 min-h-[88px]">
        {loadingSlots && (
          <div className="flex items-center gap-2 py-6 text-sm text-ink/40">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading availability…
          </div>
        )}
        {!loadingSlots && slots.length === 0 && (
          <p className="py-6 text-sm text-ink/40">Closed this day — pick another date.</p>
        )}
        {!loadingSlots && slots.length > 0 && (
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
            {slots.map((slot) => {
              const isSelected = selectedSlot?.start === slot.start;
              return (
                <button
                  key={slot.start}
                  disabled={!slot.available}
                  onClick={() => setSelectedSlot(slot)}
                  title={!slot.available ? "Already booked" : undefined}
                  className={`rounded-lg border px-2 py-2 font-mono text-xs transition ${
                    !slot.available
                      ? "cursor-not-allowed border-linen-soft bg-linen-soft text-ink/25 line-through"
                      : isSelected
                      ? "border-brass bg-brass text-white"
                      : "border-linen-soft text-ink/70 hover:border-brass hover:text-brass"
                  }`}
                >
                  {formatSlotTime(slot.start.slice(11, 16))}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Details + confirm */}
      {selectedSlot && (
        <div className="animate-fade-up border-t border-linen-soft pt-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="rounded-lg border border-linen-soft bg-linen px-3.5 py-2.5 text-sm outline-none focus:border-brass"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              type="email"
              className="rounded-lg border border-linen-soft bg-linen px-3.5 py-2.5 text-sm outline-none focus:border-brass"
            />
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Phone (optional)"
              className="rounded-lg border border-linen-soft bg-linen px-3.5 py-2.5 text-sm outline-none focus:border-brass sm:col-span-2"
            />
          </div>
          {error && <p className="mt-3 text-sm text-rust">{error}</p>}
          <button
            onClick={handleBook}
            disabled={booking || !name.trim() || !email.trim()}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-ink py-3 text-sm font-medium text-linen hover:bg-ink-soft disabled:opacity-50 sm:w-auto sm:px-8"
          >
            {booking ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {booking ? "Booking…" : `Confirm for ${formatSlotTime(selectedSlot.start.slice(11, 16))}`}
          </button>
        </div>
      )}
    </div>
  );
}

function BookingConfirmed({
  service,
  startIso,
  onReset,
}: {
  service: Service;
  startIso: string;
  onReset: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const code = useMemo(() => confirmationCode(crypto.randomUUID()), []);

  function handleAddToCalendar() {
    const ics = buildIcsFile({
      title: `${service.name} — Bright Studio`,
      description: `Appointment confirmation ${code}`,
      startIso,
      durationMinutes: service.duration_minutes,
    });
    downloadIcs(`bright-studio-${code}.ics`, ics);
  }

  return (
    <div className="animate-fade-up rounded-3xl border border-sage/30 bg-sage-soft p-8 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-sage text-white">
        <Check className="h-6 w-6" />
      </div>
      <h3 className="font-display text-2xl font-medium">You're booked!</h3>
      <p className="mt-1 text-sm text-ink/60">We'll see you then.</p>

      <div className="mx-auto mt-6 max-w-sm">
        <TicketStub
          eyebrow="Confirmed"
          title={service.name}
          accent="sage"
          stamp={
            <div className="flex items-center justify-between">
              <span>
                {new Date(startIso).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </span>
              <span className="text-ink/40">#{code}</span>
            </div>
          }
        />
      </div>

      <div className="mx-auto mt-4 flex max-w-sm gap-2">
        <button
          onClick={handleAddToCalendar}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-full bg-ink py-2.5 text-xs font-medium text-linen hover:bg-ink-soft"
        >
          <CalendarPlus className="h-3.5 w-3.5" /> Add to calendar
        </button>
        <button
          onClick={() => {
            navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="flex items-center justify-center gap-1.5 rounded-full border border-linen-soft bg-paper px-3 py-2.5 text-xs font-medium text-ink hover:bg-linen-soft"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-sage" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy code"}
        </button>
      </div>

      <button onClick={onReset} className="mt-5 text-xs font-medium text-ink/40 hover:text-ink/70">
        Book another appointment
      </button>
    </div>
  );
}
