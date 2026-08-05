import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Ticket, Lock } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

export function AdminLogin() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(username, password);
      login(res.access_token);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-linen px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-ink text-brass-soft">
            <Ticket className="h-5 w-5" />
          </div>
          <h1 className="font-display text-2xl font-medium">Staff sign in</h1>
          <p className="mt-1 text-sm text-ink/50">Bright Studio admin dashboard</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-linen-soft bg-paper p-6 shadow-sm"
        >
          <label className="block text-xs font-medium uppercase tracking-wide text-ink/50">
            Username
          </label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1.5 mb-4 w-full rounded-lg border border-linen-soft bg-linen px-3.5 py-2.5 text-sm outline-none focus:border-brass"
          />
          <label className="block text-xs font-medium uppercase tracking-wide text-ink/50">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-linen-soft bg-linen px-3.5 py-2.5 text-sm outline-none focus:border-brass"
          />

          {error && <p className="mt-3 text-sm text-rust">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-ink py-3 text-sm font-medium text-linen hover:bg-ink-soft disabled:opacity-50"
          >
            <Lock className="h-3.5 w-3.5" />
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-ink/40">
          Default seed credentials: admin / admin123 (change via .env in production)
        </p>
      </div>
    </div>
  );
}
