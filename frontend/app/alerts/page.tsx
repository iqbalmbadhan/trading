"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

const EVENT_TYPES = [
  "new_fill",
  "strategy_stopped",
  "kill_switch",
  "daily_pnl",
  "position_drawdown",
];
const CHANNELS = ["webhook", "telegram", "email"];

type Rule = {
  id: number;
  channel: string;
  event_type: string;
  rule: Record<string, number>;
  is_enabled: boolean;
};
type Log = {
  id: number;
  event_type: string;
  channel: string;
  message: string;
  status: string;
  error: string | null;
};

function AlertsView() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [form, setForm] = useState({
    channel: "webhook",
    event_type: "kill_switch",
    config: "",
  });
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRules(await apiFetch<Rule[]>("/api/v1/alerts"));
    setLogs(await apiFetch<Log[]>("/api/v1/alerts/history"));
  }, []);

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    let config: Record<string, unknown> = {};
    try {
      config = form.config ? JSON.parse(form.config) : {};
    } catch {
      setMsg("Config must be valid JSON");
      return;
    }
    try {
      await apiFetch("/api/v1/alerts", {
        method: "POST",
        body: JSON.stringify({
          channel: form.channel,
          event_type: form.event_type,
          rule: {},
          config,
        }),
      });
      setForm({ ...form, config: "" });
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function test(id: number) {
    await apiFetch(`/api/v1/alerts/${id}/test`, { method: "POST" });
    await load();
  }

  async function remove(id: number) {
    await apiFetch(`/api/v1/alerts/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Alerts</h1>

      <form
        onSubmit={create}
        className="space-y-3 rounded border border-neutral-800 bg-neutral-900 p-4"
      >
        <h2 className="font-semibold">New alert rule</h2>
        <div className="flex gap-3">
          <select
            value={form.channel}
            onChange={(e) => setForm({ ...form, channel: e.target.value })}
            className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          >
            {CHANNELS.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            value={form.event_type}
            onChange={(e) => setForm({ ...form, event_type: e.target.value })}
            className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <textarea
          value={form.config}
          onChange={(e) => setForm({ ...form, config: e.target.value })}
          placeholder='Channel config JSON, e.g. {"url":"https://discord.com/api/webhooks/..."}'
          className="h-20 w-full rounded border border-neutral-700 bg-neutral-950 px-2 py-1 font-mono text-xs"
        />
        {msg && <p className="text-sm text-red-400">{msg}</p>}
        <button className="rounded bg-emerald-600 px-4 py-1 font-medium hover:bg-emerald-500">
          Create rule
        </button>
      </form>

      <section className="space-y-2">
        <h2 className="font-semibold">Rules</h2>
        {rules.length === 0 && (
          <p className="text-sm text-neutral-500">No alert rules.</p>
        )}
        {rules.map((r) => (
          <div
            key={r.id}
            className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-900 px-4 py-2 text-sm"
          >
            <span>
              {r.event_type} → {r.channel}{" "}
              {!r.is_enabled && (
                <span className="text-neutral-500">(disabled)</span>
              )}
            </span>
            <span className="flex gap-2">
              <button
                onClick={() => test(r.id)}
                className="rounded border border-neutral-700 px-2 py-1 hover:bg-neutral-800"
              >
                Test
              </button>
              <button
                onClick={() => remove(r.id)}
                className="rounded border border-neutral-700 px-2 py-1 hover:bg-neutral-800"
              >
                Delete
              </button>
            </span>
          </div>
        ))}
      </section>

      <section className="space-y-1">
        <h2 className="font-semibold">History</h2>
        {logs.length === 0 && (
          <p className="text-sm text-neutral-500">No alerts sent yet.</p>
        )}
        {logs.map((l) => (
          <div
            key={l.id}
            className="rounded border border-neutral-800 bg-neutral-900 px-3 py-1 text-xs"
          >
            <span
              className={
                l.status === "sent" ? "text-emerald-400" : "text-red-400"
              }
            >
              {l.status}
            </span>{" "}
            <span className="text-neutral-400">
              [{l.event_type}/{l.channel}]
            </span>{" "}
            {l.message}
            {l.error && <span className="text-red-400"> — {l.error}</span>}
          </div>
        ))}
      </section>
    </main>
  );
}

export default function AlertsPage() {
  return <RequireAuth>{() => <AlertsView />}</RequireAuth>;
}
