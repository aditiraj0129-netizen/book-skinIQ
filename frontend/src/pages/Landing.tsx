import { useEffect, useState } from "react";
import { Sparkles, MapPin, Phone } from "lucide-react";
import { Nav } from "../components/Nav";
import { TicketStub } from "../components/TicketStub";
import { ChatWidget } from "../components/ChatWidget";
import { BookingCalendar } from "../components/BookingCalendar";
import { ReviewsSection } from "../components/ReviewsSection";
import { MyAppointments } from "../components/MyAppointments";
import { useUserAuth } from "../lib/userAuth";
import { api } from "../lib/api";
import type { BusinessInfo, Service } from "../lib/types";
import { formatDuration, formatPrice } from "../lib/format";

const FAQ_ITEMS = [
  {
    q: "Can I cancel or reschedule for free?",
    a: "Yes — cancel up to 4 hours before your appointment at no charge. Manage both from your appointments list once you're signed in.",
  },
  {
    q: "Do I need to bring anything?",
    a: "Just yourself. For massages, arrive 10 minutes early for a quick first-visit questionnaire.",
  },
  {
    q: "How far ahead can I book?",
    a: "Anywhere from right now up to 30 days ahead, during business hours — the calendar only shows real, open slots.",
  },
];

export function Landing() {
  const { user } = useUserAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [business, setBusiness] = useState<BusinessInfo | null>(null);
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  useEffect(() => {
    api.listServices().then(setServices).catch(() => setServices([]));
    api.getBusinessInfo().then(setBusiness).catch(() => setBusiness(null));
  }, []);

  const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="min-h-screen bg-linen text-ink">
      <Nav />

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl gap-12 px-6 pb-16 pt-16 sm:pt-20 lg:grid-cols-2 lg:items-center">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-brass/30 bg-brass/10 px-3 py-1 text-xs font-medium text-brass">
            <Sparkles className="h-3 w-3" /> Real-time availability, no back-and-forth
          </span>
          <h1 className="mt-5 font-display text-5xl font-medium leading-[1.05] tracking-tight sm:text-6xl">
            {user ? `Welcome back, ${user.name.split(" ")[0]}.` : "Booking, the way it should feel."}
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-ink/65">
            Pick a service and a time on the calendar — every slot you see is really open. Ask
            Aria if you want to know more before you book.
          </p>
          {business && (
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink/50">
              <span className="flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" /> {business.phone || "—"}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" /> {business.address || "—"}
              </span>
              <span className="font-mono">
                {business.open_hour}:00–{business.close_hour}:00 ·{" "}
                {business.open_days.map((d) => dayNames[d]).join(" ")}
              </span>
            </div>
          )}
        </div>

        <div className="hidden lg:block" aria-hidden="true">
          {services.slice(0, 1).map((s) => (
            <div key={s.id} className="animate-drift">
              <TicketStub
                eyebrow="Popular"
                title={s.name}
                subtitle={s.description}
                accent="brass"
                stamp={
                  <div className="flex items-center justify-between">
                    <span>{formatDuration(s.duration_minutes)}</span>
                    <span>{formatPrice(s.price)}</span>
                  </div>
                }
              />
            </div>
          ))}
        </div>
      </section>

      {/* Booking calendar - the primary path */}
      <section id="book" className="mx-auto max-w-3xl px-6 pb-16">
        {services.length > 0 ? (
          <BookingCalendar services={services} selectedServiceId={selectedServiceId} />
        ) : (
          <p className="text-sm text-ink/50">Loading services…</p>
        )}
      </section>

      <MyAppointments />

      {/* Services */}
      <section id="services" className="mx-auto max-w-6xl px-6 py-16">
        <p className="font-mono text-xs uppercase tracking-widest text-ink/40">What we offer</p>
        <h2 className="mt-2 font-display text-3xl font-medium">Our services</h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {services.map((s, i) => (
            <TicketStub
              key={s.id}
              eyebrow="Bright Studio"
              title={s.name}
              subtitle={s.description}
              accent={(["brass", "sage", "rust", "ink"] as const)[i % 4]}
              stamp={
                <div className="flex items-center justify-between">
                  <span>{formatDuration(s.duration_minutes)}</span>
                  <span>{formatPrice(s.price)}</span>
                </div>
              }
              onClick={() => {
                setSelectedServiceId(s.id);
                document.getElementById("book")?.scrollIntoView({ behavior: "smooth" });
              }}
            />
          ))}
        </div>
      </section>

      <ReviewsSection />

      {/* FAQ */}
      <section id="faq" className="mx-auto max-w-3xl px-6 py-16">
        <p className="font-mono text-xs uppercase tracking-widest text-ink/40">Good to know</p>
        <h2 className="mt-2 font-display text-3xl font-medium">Frequently asked</h2>
        <div className="mt-8 divide-y divide-linen-soft border-y border-linen-soft">
          {FAQ_ITEMS.map((item, i) => (
            <div key={item.q}>
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="flex w-full items-center justify-between py-4 text-left"
                aria-expanded={openFaq === i}
              >
                <span className="font-medium">{item.q}</span>
                <span className="text-ink/40">{openFaq === i ? "−" : "+"}</span>
              </button>
              {openFaq === i && <p className="animate-fade-up pb-4 text-sm leading-relaxed text-ink/60">{item.a}</p>}
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-ink/40">Ask Aria anything else — she pulls from the same source.</p>
      </section>

      <footer className="border-t border-linen-soft py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-ink/50 sm:flex-row">
          <span>© {new Date().getFullYear()} {business?.business_name || "Bright Studio"}</span>
          {business && (
            <span>
              {business.open_hour}:00–{business.close_hour}:00, {business.open_days.map((d) => dayNames[d]).join("–")}
            </span>
          )}
        </div>
      </footer>

      <ChatWidget />
    </div>
  );
}
