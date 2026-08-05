import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Moon, Sun, Ticket } from "lucide-react";
import { UserLoginBar } from "./UserLoginBar";

export function Nav() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <header className="sticky top-0 z-30 border-b border-linen-soft/80 bg-linen/85 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-brass-soft">
            <Ticket className="h-4 w-4" />
          </div>
          <span className="font-display text-lg font-medium tracking-tight">Bright Studio</span>
        </Link>

        <div className="hidden items-center gap-8 text-sm font-medium text-ink/70 lg:flex">
          <a href="#book" className="hover:text-ink">Book</a>
          <a href="#services" className="hover:text-ink">Services</a>
          <a href="#reviews" className="hover:text-ink">Reviews</a>
          <a href="#faq" className="hover:text-ink">FAQ</a>
        </div>

        <div className="flex items-center gap-3">
          <UserLoginBar />
          <button
            onClick={() => setDark((d) => !d)}
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-linen-soft text-ink/70 hover:bg-linen-soft sm:flex"
            aria-label="Toggle dark mode"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <Link
            to="/admin"
            className="hidden rounded-full border border-ink/15 px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-linen transition-colors sm:block"
          >
            Staff login
          </Link>
        </div>
      </nav>
    </header>
  );
}
