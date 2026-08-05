import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { api } from "../lib/api";
import type { Review } from "../lib/types";

export function ReviewsSection() {
  const [reviews, setReviews] = useState<Review[]>([]);

  useEffect(() => {
    api.listReviews().then(setReviews).catch(() => setReviews([]));
  }, []);

  if (reviews.length === 0) return null;

  const avg = reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length;

  return (
    <section id="reviews" className="border-y border-linen-soft bg-paper py-16">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mb-10 flex items-end justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink/40">Word of mouth</p>
            <h2 className="mt-2 font-display text-3xl font-medium">What people say</h2>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star
                  key={i}
                  className={`h-4 w-4 ${i < Math.round(avg) ? "fill-brass text-brass" : "text-linen-soft"}`}
                />
              ))}
            </div>
            <span className="font-mono text-sm text-ink/50">{avg.toFixed(1)} / 5</span>
          </div>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {reviews.slice(0, 4).map((r) => (
            <div key={r.id} className="rounded-2xl border border-linen-soft bg-linen p-5">
              <div className="mb-3 flex">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star key={i} className={`h-3.5 w-3.5 ${i < r.rating ? "fill-brass text-brass" : "text-linen-soft"}`} />
                ))}
              </div>
              <p className="text-sm leading-relaxed text-ink/70">"{r.comment}"</p>
              <p className="mt-3 font-mono text-xs text-ink/40">
                {r.customer_name}
                {r.service_name ? ` · ${r.service_name}` : ""}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
