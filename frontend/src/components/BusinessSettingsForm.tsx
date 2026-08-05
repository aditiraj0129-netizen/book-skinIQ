import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { BusinessInfo } from "../lib/types";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function BusinessSettingsForm({ refreshKey }: { refreshKey?: number }) {
  const { token } = useAuth();
  const [form, setForm] = useState<BusinessInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.admin.getBusinessSettings(token).then(setForm);
  }, [token, refreshKey]);

  if (!form) return <p className="text-sm text-ink/50">Loading…</p>;

  function toggleDay(day: number) {
    if (!form) return;
    const open_days = form.open_days.includes(day)
      ? form.open_days.filter((d) => d !== day)
      : [...form.open_days, day].sort();
    setForm({ ...form, open_days });
  }

  async function handleSave() {
    if (!token || !form) return;
    setSaving(true);
    try {
      const updated = await api.admin.updateBusinessSettings(token, form);
      setForm(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-linen-soft bg-paper p-5">
      <h3 className="mb-4 font-display text-lg font-medium">Business settings</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Business name" value={form.business_name} onChange={(v) => setForm({ ...form, business_name: v })} />
        <Field label="Tagline" value={form.tagline} onChange={(v) => setForm({ ...form, tagline: v })} />
        <Field label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
        <Field label="Address" value={form.address} onChange={(v) => setForm({ ...form, address: v })} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-ink/50">Open hour</label>
          <input
            type="number"
            min={0}
            max={23}
            value={form.open_hour}
            onChange={(e) => setForm({ ...form, open_hour: Number(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-linen-soft bg-linen px-3 py-2 text-sm outline-none focus:border-brass"
          />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-ink/50">Close hour</label>
          <input
            type="number"
            min={1}
            max={24}
            value={form.close_hour}
            onChange={(e) => setForm({ ...form, close_hour: Number(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-linen-soft bg-linen px-3 py-2 text-sm outline-none focus:border-brass"
          />
        </div>
      </div>

      <div className="mt-4">
        <label className="text-xs font-medium uppercase tracking-wide text-ink/50">Open days</label>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {DAY_LABELS.map((label, i) => (
            <button
              key={label}
              onClick={() => toggleDay(i)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                form.open_days.includes(i) ? "bg-ink text-linen" : "border border-linen-soft text-ink/50 hover:bg-linen-soft"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-5 flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-linen hover:bg-ink-soft disabled:opacity-50"
      >
        <Save className="h-3.5 w-3.5" />
        {saving ? "Saving…" : saved ? "Saved!" : "Save changes"}
      </button>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-linen-soft bg-linen px-3 py-2 text-sm outline-none focus:border-brass"
      />
    </div>
  );
}
