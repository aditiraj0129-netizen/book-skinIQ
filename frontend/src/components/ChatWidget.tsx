import { useEffect, useRef, useState } from "react";
import { Send, X, Sparkles } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import type { ChatMessageUI } from "../lib/types";

function uid() {
  return crypto.randomUUID();
}

const QUICK_PROMPTS = ["What are your hours?", "What do people say about you?", "What should I bring?"];

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageUI[]>([
    {
      id: uid(),
      role: "assistant",
      text: "Hi, I'm Aria. Ask me about our services, hours, availability, or what people say — when you're ready to book, use the calendar above.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [engine, setEngine] = useState<"grok" | "fallback" | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setInput("");
    setMessages((m) => [...m, { id: uid(), role: "user", text: trimmed, timestamp: Date.now() }]);
    setSending(true);
    try {
      const res = await api.sendChatMessage(trimmed, sessionId);
      setSessionId(res.session_id);
      setEngine(res.engine);
      setMessages((m) => [...m, { id: uid(), role: "assistant", text: res.reply, timestamp: Date.now() }]);
    } catch {
      setMessages((m) => [
        ...m,
        { id: uid(), role: "assistant", text: "Sorry, I couldn't reach the assistant just now.", timestamp: Date.now() },
      ]);
    } finally {
      setSending(false);
    }
  }

  const showPrompts = messages.length === 1;

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-ink px-5 py-3.5 text-linen shadow-xl transition-transform hover:scale-105 focus-visible:outline-brass"
          aria-label="Ask Aria about services, hours, and reviews"
        >
          <Sparkles className="h-4 w-4 text-brass-soft" />
          <span className="text-sm font-medium">Ask Aria</span>
        </button>
      )}

      <div
        className={clsx(
          "fixed bottom-0 right-0 z-50 flex h-[100dvh] w-full flex-col border-linen-soft bg-paper shadow-2xl transition-transform duration-300 ease-out sm:bottom-6 sm:right-6 sm:h-[600px] sm:w-[380px] sm:rounded-2xl sm:border",
          open ? "translate-y-0" : "translate-y-full sm:translate-y-[110%]"
        )}
        role="dialog"
        aria-label="Ask Aria"
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between border-b border-linen-soft bg-ink px-4 py-3.5 text-linen sm:rounded-t-2xl">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brass/20">
              <Sparkles className="h-4 w-4 text-brass-soft" />
            </div>
            <div>
              <p className="font-display text-sm font-medium leading-tight">Aria</p>
              <p className="text-[11px] text-linen/60">
                {engine === "grok" ? "Powered by Grok" : engine === "fallback" ? "Rule-based mode" : "Ask about services & hours"}
              </p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="rounded-full p-1.5 text-linen/70 hover:bg-white/10 hover:text-linen"
            aria-label="Close chat"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.map((m) => (
            <div key={m.id} className={clsx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={clsx(
                  "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                  m.role === "user" ? "rounded-br-sm bg-brass text-white" : "rounded-bl-sm bg-linen-soft text-ink"
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

          {showPrompts && !sending && (
            <div className="flex flex-wrap gap-2 pt-1">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  className="rounded-full border border-brass/40 bg-brass/10 px-3 py-1.5 text-xs font-medium text-brass hover:bg-brass/20"
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="flex items-center gap-2 border-t border-linen-soft p-3 sm:rounded-b-2xl"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about services, hours…"
            className="flex-1 rounded-full border border-linen-soft bg-linen px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink/40 focus:border-brass"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-linen transition hover:bg-ink-soft disabled:opacity-40"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>

      {open && (
        <button className="fixed inset-0 z-40 bg-ink/20 sm:hidden" onClick={() => setOpen(false)} aria-label="Close chat" />
      )}
    </>
  );
}
