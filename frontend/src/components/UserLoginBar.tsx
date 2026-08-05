import { useState } from "react";
import { User, X } from "lucide-react";
import { useUserAuth } from "../lib/userAuth";

export function UserLoginBar() {
  const { user, login, logout, loading } = useUserAuth();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  if (user) {
    return (
      <div className="flex items-center gap-3 rounded-full border border-linen-soft bg-paper py-1.5 pl-1.5 pr-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brass/15 text-brass">
          <User className="h-3.5 w-3.5" />
        </div>
        <span className="text-sm font-medium">Hi, {user.name.split(" ")[0]} 👋</span>
        <button onClick={logout} className="text-xs text-ink/40 hover:text-ink/70">
          Not you?
        </button>
      </div>
    );
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-full border border-linen-soft px-4 py-2 text-sm font-medium text-ink/70 hover:bg-linen-soft"
      >
        <User className="h-3.5 w-3.5" /> Sign in
      </button>
    );
  }

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        await login(name.trim(), email.trim() || undefined);
        setOpen(false);
      }}
      className="flex items-center gap-2 rounded-full border border-linen-soft bg-paper py-1.5 pl-4 pr-1.5 shadow-sm"
    >
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Your name"
        className="w-24 bg-transparent text-sm outline-none placeholder:text-ink/35"
      />
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email (optional)"
        className="hidden w-36 bg-transparent text-sm outline-none placeholder:text-ink/35 sm:block"
      />
      <button
        type="submit"
        disabled={!name.trim() || loading}
        className="rounded-full bg-ink px-3.5 py-1.5 text-xs font-medium text-linen disabled:opacity-40"
      >
        {loading ? "…" : "Go"}
      </button>
      <button
        type="button"
        onClick={() => setOpen(false)}
        className="flex h-6 w-6 items-center justify-center rounded-full text-ink/40 hover:text-ink/70"
        aria-label="Cancel"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </form>
  );
}
