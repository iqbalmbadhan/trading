"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Strategy = {
  id: number;
  name: string;
  type: string;
  symbol: string;
  timeframe: string;
  is_paper: boolean;
  is_active: boolean;
  version: number;
};

type Template = {
  type: string;
  default_params: Record<string, number>;
};

function StrategiesView() {
  const [items, setItems] = useState<Strategy[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [form, setForm] = useState({
    name: "",
    type: "ma_crossover",
    symbol: "BTC/USDT",
    timeframe: "1h",
  });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setItems(await apiFetch<Strategy[]>("/api/v1/strategies"));
  }, []);

  useEffect(() => {
    apiFetch<Template[]>("/api/v1/strategies/templates")
      .then(setTemplates)
      .catch((e) => setError(e.message));
    load().catch((e) => setError(e.message));
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const tpl = templates.find((t) => t.type === form.type);
    try {
      await apiFetch<Strategy>("/api/v1/strategies", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          params: tpl ? tpl.default_params : {},
        }),
      });
      setForm({ ...form, name: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function toggle(s: Strategy) {
    const action = s.is_active ? "stop" : "start";
    try {
      await apiFetch(`/api/v1/strategies/${s.id}/${action}`, {
        method: "POST",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Strategies</h1>

      <div className="rounded border border-sky-800 bg-sky-950/40 p-3 text-sm text-sky-300">
        All strategies run in <strong>paper mode</strong>. Live trading is a
        separate, explicitly-confirmed action introduced later.
      </div>

      <section className="space-y-2">
        {items.length === 0 && (
          <p className="text-sm text-neutral-500">No strategies yet.</p>
        )}
        {items.map((s) => (
          <div
            key={s.id}
            className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-900 px-4 py-3"
          >
            <span>
              <span className="font-medium">{s.name}</span>{" "}
              <span className="text-neutral-500">
                {s.type} · {s.symbol} · {s.timeframe} · v{s.version}
              </span>
              {s.is_active && (
                <span className="ml-2 text-xs text-emerald-400">running</span>
              )}
            </span>
            <button
              onClick={() => toggle(s)}
              className="rounded border border-neutral-700 px-3 py-1 text-sm hover:bg-neutral-800"
            >
              {s.is_active ? "Stop" : "Start"}
            </button>
          </div>
        ))}
      </section>

      <form
        onSubmit={create}
        className="space-y-3 rounded border border-neutral-800 bg-neutral-900 p-4"
      >
        <h2 className="font-semibold">New strategy</h2>
        <input
          required
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        <select
          value={form.type}
          onChange={(e) => setForm({ ...form, type: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        >
          {templates.map((t) => (
            <option key={t.type} value={t.type}>
              {t.type}
            </option>
          ))}
        </select>
        <input
          required
          placeholder="Symbol (e.g. BTC/USDT)"
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        <input
          required
          placeholder="Timeframe (e.g. 1h)"
          value={form.timeframe}
          onChange={(e) => setForm({ ...form, timeframe: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          className="rounded bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          Create (paper)
        </button>
      </form>
    </main>
  );
}

export default function StrategiesPage() {
  return <RequireAuth>{() => <StrategiesView />}</RequireAuth>;
}
