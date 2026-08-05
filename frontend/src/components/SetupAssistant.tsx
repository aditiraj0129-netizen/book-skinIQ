import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { ChatMessageUI } from "../lib/types";

function uid() {
  return crypto.randomUUID();
}

const EXAMPLES = [
  "We're open 8 to 6, Monday to Saturday",
  "Add service Yoga Class, 60 min, $40",
  "What are our current settings?",
];

export function SetupAssistant({ onSettingsChanged }: { onSettingsChanged?: () => void }) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessageUI[]>([
    {
      id: uid(),
      role: "assistant",
      text: "Tell me how you'd like to configure the business — hours, services, or general info.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [engine, setEngine] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending || !token) return;
    setInput("");
    setMessages((m) => [...m, { id: uid(), role: "user", text: trimmed, timestamp: Date.now() }]);
    setSending(true);
    try {
      const res = await api.admin.setupChat(token, trimmed, sessionId);
      setSessionId(res.session_id);
      setEngine(res.engine);
      setMessages((m) => [...m, { id: uid(), role: "assistant", text: res.reply, timestamp: Date.now() }]);
      onSettingsChanged?.();
    } catch {
      setMessages((m) => [
        ...m,
        { id: uid(), role: "assistant", text: "Something went wrong — please try again.", timestamp: Date.now() },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[520px] flex-col rounded-2xl border border-linen-soft bg-paper">
      <div className="flex items-center justify-between border-b border-linen-soft px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brass" />
          <span className="font-display text-sm font-medium">Setup Assistant</span>
        </div>
        {engine && (
          <span className="rounded-full bg-linen-soft px-2.5 py-0.5 text-[11px] font-medium text-ink/50">
            {engine === "grok" ? "Grok" : "Rule-based"}
          </span>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.map((m) => (
          <div key={m.id} className={clsx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={clsx(
                "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                m.role === "user" ? "rounded-br-sm bg-ink text-linen" : "rounded-bl-sm bg-linen-soft text-ink"
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-linen-soft px-4 py-3">
              <span className="h-1.5 w-1.5 animate-typing rounded-full bg-ink/40 [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 animate-typing rounded-full bg-ink/40 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-typing rounded-full bg-ink/40 [animation-delay:300ms]" />
            </div>
          </div>
        )}
        {messages.length === 1 && !sending && (
          <div className="flex flex-col gap-2 pt-1">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => send(ex)}
                className="rounded-lg border border-linen-soft px-3 py-2 text-left text-xs text-ink/60 hover:border-brass hover:text-brass"
              >
                "{ex}"
              </button>
            ))}
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-linen-soft p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. we're open 9 to 6, Mon-Fri"
          className="flex-1 rounded-full border border-linen-soft bg-linen px-4 py-2.5 text-sm outline-none focus:border-brass"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-linen hover:bg-ink-soft disabled:opacity-40"
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
