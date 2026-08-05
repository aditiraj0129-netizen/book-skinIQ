import { useEffect, useState } from "react";
import { CalendarClock, X } from "lucide-react";
import { api } from "../lib/api";
import { useUserAuth } from "../lib/userAuth";
import type { Appointment } from "../lib/types";
import { formatDateTime } from "../lib/format";
import { TicketStub } from "./TicketStub";

export function MyAppointments() {
  const { user } = useUserAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    if (!user?.email) return;
    setLoading(true);
    try {
      const all = await api.getUserAppointments(user.email);
      setAppointments(all.filter((a) => a.status === "confirmed"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.email]);

  async function handleCancel(id: string) {
    setBusyId(id);
    try {
      await api.cancelBooking(id);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  if (!user?.email) return null;
  if (!loading && appointments.length === 0) return null;

  return (
    <section className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-5 flex items-center gap-2">
        <CalendarClock className="h-4 w-4 text-brass" />
        <h2 className="font-display text-xl font-medium">Your upcoming appointments</h2>
      </div>
      <div className="space-y-3">
        {appointments.map((a) => (
          <div key={a.id} className="flex items-center gap-3">
            <div className="flex-1">
              <TicketStub
                eyebrow={a.service.name}
                title={formatDateTime(a.start_time)}
                accent="brass"
                stamp={<span>{a.customer.name}</span>}
              />
            </div>
            <button
              onClick={() => handleCancel(a.id)}
              disabled={busyId === a.id}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-rust/30 text-rust hover:bg-rust-soft disabled:opacity-40"
              aria-label="Cancel appointment"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
