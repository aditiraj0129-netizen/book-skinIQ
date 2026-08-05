import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LogOut, Ticket, XCircle, CheckCircle2, UserX } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Appointment, AppointmentStatus, DashboardStats } from "../lib/types";
import { formatDateTime, formatPrice } from "../lib/format";
import { TicketStub } from "../components/TicketStub";
import { SetupAssistant } from "../components/SetupAssistant";
import { BusinessSettingsForm } from "../components/BusinessSettingsForm";

const STATUS_TABS: { key: AppointmentStatus | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "confirmed", label: "Confirmed" },
  { key: "completed", label: "Completed" },
  { key: "cancelled", label: "Cancelled" },
  { key: "no_show", label: "No-show" },
];

const CHART_COLORS = ["#b8862e", "#5f7a5c", "#a1432e", "#2c3654"];

export function AdminDashboard() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [tab, setTab] = useState<AppointmentStatus | "all">("all");
  const [view, setView] = useState<"overview" | "setup" | "settings">("overview");
  const [settingsRefreshKey, setSettingsRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [s, a] = await Promise.all([
        api.admin.stats(token),
        api.admin.listAppointments(token, tab === "all" ? undefined : tab),
      ]);
      setStats(s);
      setAppointments(a);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        navigate("/admin");
        return;
      }
      setError("Couldn't load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [token, tab, logout, navigate]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAction(id: string, action: "cancel" | "complete" | "noShow") {
    if (!token) return;
    setActionId(id);
    try {
      await api.admin[action](token, id);
      await load();
    } catch {
      setError("That action failed — please try again.");
    } finally {
      setActionId(null);
    }
  }

  const dayChartData = stats
    ? Object.entries(stats.bookings_by_day)
        .sort(([a], [b]) => a.localeCompare(b))
        .slice(-7)
        .map(([date, count]) => ({ date: date.slice(5), count }))
    : [];

  const serviceChartData = stats
    ? Object.entries(stats.bookings_by_service).map(([name, count]) => ({ name, count }))
    : [];

  return (
    <div className="min-h-screen bg-linen">
      {/* Top bar */}
      <header className="border-b border-linen-soft bg-paper">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-brass-soft">
              <Ticket className="h-4 w-4" />
            </div>
            <span className="font-display text-lg font-medium">Bright Studio — Admin</span>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/admin");
            }}
            className="flex items-center gap-1.5 rounded-full border border-linen-soft px-3.5 py-2 text-sm text-ink/70 hover:bg-linen-soft"
          >
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {error && (
          <div className="mb-6 rounded-lg border border-rust/30 bg-rust-soft px-4 py-3 text-sm text-rust">
            {error}
          </div>
        )}

        {/* View switcher */}
        <div className="mb-8 flex gap-2">
          {[
            { key: "overview", label: "Overview" },
            { key: "setup", label: "Setup Assistant" },
            { key: "settings", label: "Business Settings" },
          ].map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key as typeof view)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                view === v.key ? "bg-ink text-linen" : "border border-linen-soft text-ink/60 hover:bg-linen-soft"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>

        {view === "setup" && (
          <div className="max-w-xl">
            <SetupAssistant onSettingsChanged={() => setSettingsRefreshKey((k) => k + 1)} />
          </div>
        )}

        {view === "settings" && (
          <div className="max-w-xl">
            <BusinessSettingsForm refreshKey={settingsRefreshKey} />
          </div>
        )}

        {view === "overview" && (
          <>
        {/* Stats strip */}
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Today" value={stats?.bookings_today} />
          <StatCard label="Upcoming" value={stats?.upcoming_appointments} accent="sage" />
          <StatCard label="Cancelled" value={stats?.cancelled_appointments} accent="rust" />
          <StatCard label="Busiest hour" value={stats?.busiest_hour ?? "—"} accent="brass" isText />
        </div>

        {/* Charts */}
        <div className="mb-10 grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-linen-soft bg-paper p-5">
            <h3 className="mb-4 font-display text-lg font-medium">Bookings, last 7 days</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={dayChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#efe7d8" />
                <XAxis dataKey="date" fontSize={12} stroke="#17203a99" />
                <YAxis allowDecimals={false} fontSize={12} stroke="#17203a99" />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#efe7d8", fontSize: 13 }} />
                <Bar dataKey="count" fill="#b8862e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-2xl border border-linen-soft bg-paper p-5">
            <h3 className="mb-4 font-display text-lg font-medium">Bookings by service</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={serviceChartData}
                  dataKey="count"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                >
                  {serviceChartData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#efe7d8", fontSize: 13 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Appointments */}
        <div className="mb-4 flex flex-wrap gap-2">
          {STATUS_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                tab === t.key ? "bg-ink text-linen" : "border border-linen-soft text-ink/60 hover:bg-linen-soft"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {loading && <p className="text-sm text-ink/50">Loading…</p>}
          {!loading && appointments.length === 0 && (
            <p className="rounded-xl border border-dashed border-linen-soft py-10 text-center text-sm text-ink/40">
              No appointments here yet.
            </p>
          )}
          {appointments.map((a) => (
            <div key={a.id} className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex-1">
                <TicketStub
                  eyebrow={a.status.replace("_", " ")}
                  title={a.service.name}
                  subtitle={`${a.customer.name} · ${a.customer.email}`}
                  accent={
                    a.status === "confirmed"
                      ? "brass"
                      : a.status === "completed"
                      ? "sage"
                      : a.status === "cancelled"
                      ? "rust"
                      : "ink"
                  }
                  meta={<span className="font-mono text-sm text-ink/40">{formatPrice(a.service.price)}</span>}
                  stamp={<span>{formatDateTime(a.start_time)}</span>}
                />
              </div>
              {a.status === "confirmed" && (
                <div className="flex shrink-0 gap-2 sm:flex-col">
                  <ActionButton
                    icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    label="Complete"
                    onClick={() => handleAction(a.id, "complete")}
                    disabled={actionId === a.id}
                  />
                  <ActionButton
                    icon={<UserX className="h-3.5 w-3.5" />}
                    label="No-show"
                    onClick={() => handleAction(a.id, "noShow")}
                    disabled={actionId === a.id}
                  />
                  <ActionButton
                    icon={<XCircle className="h-3.5 w-3.5" />}
                    label="Cancel"
                    onClick={() => handleAction(a.id, "cancel")}
                    disabled={actionId === a.id}
                    danger
                  />
                </div>
              )}
            </div>
          ))}
        </div>
        </>
        )}
      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = "ink",
  isText = false,
}: {
  label: string;
  value: string | number | undefined;
  accent?: "ink" | "sage" | "rust" | "brass";
  isText?: boolean;
}) {
  const colorMap = { ink: "text-ink", sage: "text-sage", rust: "text-rust", brass: "text-brass" };
  return (
    <div className="rounded-2xl border border-linen-soft bg-paper p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-ink/40">{label}</p>
      <p className={`mt-1.5 font-display ${isText ? "text-2xl" : "text-3xl"} font-medium ${colorMap[accent]}`}>
        {value ?? "—"}
      </p>
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
  disabled,
  danger = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-1.5 rounded-full border px-3 py-2 text-xs font-medium transition disabled:opacity-40 ${
        danger
          ? "border-rust/30 text-rust hover:bg-rust-soft"
          : "border-linen-soft text-ink/70 hover:bg-linen-soft"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
