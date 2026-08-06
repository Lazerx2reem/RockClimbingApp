"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { STARTER_PROMPTS, toolLabel, toolSummary } from "@/lib/coach";
import type { CoachMessage, CoachStatus, Conversation } from "@/lib/types";

export default function CoachPage() {
  const [status, setStatus] = useState<CoachStatus | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<CoachMessage[]>([]);
  const [input, setInput] = useState("");
  // Live reply being streamed, plus which tools it has reached for so far.
  const [streaming, setStreaming] = useState<string | null>(null);
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.coachStatus().then(setStatus).catch(() => {});
    api
      .listConversations()
      .then((list) => {
        setConversations(list);
        if (list.length) void selectConversation(list[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  // Keep the newest content in view as the reply streams in.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming, activeTools]);

  async function selectConversation(id: number) {
    setActiveId(id);
    setError(null);
    const conversation = await api.getConversation(id);
    setMessages(conversation.messages);
  }

  function startNew() {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this conversation?")) return;
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (id === activeId) startNew();
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;

    setBusy(true);
    setError(null);
    setInput("");
    setStreaming("");
    setActiveTools([]);

    try {
      // A conversation is created lazily, so an abandoned "New chat" leaves
      // nothing behind.
      let conversationId = activeId;
      if (conversationId === null) {
        const created = await api.createConversation();
        conversationId = created.id;
        setActiveId(created.id);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: -Date.now(), // placeholder until the transcript is reloaded
          role: "user",
          content,
          tool_calls: null,
          created_at: new Date().toISOString(),
        },
      ]);

      let reply = "";
      const tools: string[] = [];

      for await (const event of api.sendCoachMessage(conversationId, content)) {
        if (event.type === "delta") {
          reply += event.text;
          setStreaming(reply);
        } else if (event.type === "tool") {
          tools.push(event.name);
          setActiveTools([...tools]);
        } else if (event.type === "error") {
          setError(event.message);
          setStreaming(null);
          return;
        } else if (event.type === "done") {
          setMessages((prev) => [
            ...prev,
            {
              id: event.message_id,
              role: "assistant",
              content: reply,
              tool_calls: tools.map((name) => ({ name, input: {} })),
              created_at: new Date().toISOString(),
            },
          ]);
          setStreaming(null);
        }
      }

      // Titles are derived server-side from the first message.
      setConversations(await api.listConversations());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The coach is unreachable.");
      setStreaming(null);
    } finally {
      setBusy(false);
      setActiveTools([]);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  const isEmpty = messages.length === 0 && streaming === null;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Coach</h1>
        <button onClick={startNew} disabled={busy} className="btn-primary">
          New chat
        </button>
      </div>
      <p className="mt-1 max-w-2xl text-sm text-steel-500">
        Ask about your training and the coach will read your own logbook,
        sessions, and video analyses before answering.
      </p>

      {status && !status.available && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          The coach isn&apos;t configured yet. Set <code>ANTHROPIC_API_KEY</code> in{" "}
          <code>backend/.env</code> and restart the API.
        </p>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* Conversation list */}
        <aside className="space-y-1 lg:col-span-1">
          {conversations.length === 0 && (
            <p className="text-sm text-steel-400">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center gap-1 rounded-lg px-3 py-2 text-sm transition-colors ${
                c.id === activeId
                  ? "bg-lake-50 text-lake-700"
                  : "text-steel-600 hover:bg-steel-100"
              }`}
            >
              <button
                onClick={() => void selectConversation(c.id)}
                disabled={busy}
                className="min-w-0 flex-1 truncate text-left font-medium"
              >
                {c.title}
              </button>
              <button
                onClick={() => void onDelete(c.id)}
                aria-label={`Delete ${c.title}`}
                className="text-xs text-steel-400 opacity-0 transition-opacity hover:text-red-600 group-hover:opacity-100"
              >
                ✕
              </button>
            </div>
          ))}
        </aside>

        {/* Transcript */}
        <section className="card flex min-h-[28rem] flex-col lg:col-span-3">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {isEmpty && (
              <div className="py-8 text-center">
                <p className="text-sm text-steel-500">
                  Ask anything about your climbing. A few places to start:
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => void send(prompt)}
                      disabled={busy || status?.available === false}
                      className="rounded-full border border-steel-200 px-3 py-1.5 text-sm text-steel-600 transition-colors hover:border-lake-300 hover:bg-lake-50 hover:text-lake-700 disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={m.role === "user" ? "flex justify-end" : undefined}
              >
                {m.role === "assistant" && toolSummary(m.tool_calls) && (
                  <p className="mb-1.5 text-xs text-steel-400">
                    {toolSummary(m.tool_calls)}
                  </p>
                )}
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-lake-600 px-4 py-2.5 text-sm text-white"
                      : "whitespace-pre-wrap text-sm leading-relaxed text-steel-700"
                  }
                >
                  {m.content}
                </div>
              </div>
            ))}

            {streaming !== null && (
              <div>
                {activeTools.length > 0 && (
                  <p className="mb-1.5 text-xs text-steel-400">
                    Checking{" "}
                    {Array.from(new Set(activeTools)).map(toolLabel).join(", ")}…
                  </p>
                )}
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-steel-700">
                  {streaming}
                  <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-lake-500 align-text-bottom" />
                </div>
              </div>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}
            <div ref={bottom} />
          </div>

          <form
            onSubmit={onSubmit}
            className="flex items-end gap-2 border-t border-steel-200 p-3"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder="Ask your coach… (Enter to send, Shift+Enter for a new line)"
              disabled={busy || status?.available === false}
              className="field mt-0 flex-1 resize-none"
            />
            <button
              type="submit"
              disabled={busy || !input.trim() || status?.available === false}
              className="btn-primary"
            >
              {busy ? "…" : "Send"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
