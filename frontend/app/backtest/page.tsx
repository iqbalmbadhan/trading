"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Backtest = {
  id: number;
  type: string;
  symbol: string;
  timeframe: string;
  status: string;
  error: string | null;
  metrics: Record<string, number>;
  monte_carlo: Record<string, number>;
};

function BacktestView() {
  const [items, setItems] = useState<Backtest[]>([]);
  const [selected, setSelected] = useState<Backtest | null>(null);
  const [form, setForm] = useState({
    type: "ma_crossover",
    symbol: "BTC/USDT",
    timeframe: "1h",
    starting_cash: 10000,
  });
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setItems(await apiFetch<Backtest[]>("/api/v1/backtests"));
  }, []);

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await apiFetch<Backtest>("/api/v1/backtests", {
        method: "POST",
        body: JSON.stringify({
          type: form.type,
          symbol: form.symbol,
          timeframe: form.timeframe,
          starting_cash: Number(form.starting_cash),
          params: {},
        }),
      });
      await load();
      setMsg("Backtest queued. Refresh to see results.");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function open(id: number) {
    setSelected(await apiFetch<Backtest>(`/api/v1/backtests/${id}`));
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Backtesting</h1>

      <form
        onSubmit={create}
        className="flex flex-wrap items-end gap-3 rounded border border-neutral-800 bg-neutral-900 p-4"
      >
        <input
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value })}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          placeholder="Symbol"
        />
        <input
          value={form.timeframe}
          onChange={(e) => setForm({ ...form, timeframe: e.target.value })}
          className="w-20 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          placeholder="TF"
        />
        <input
          type="number"
          value={form.starting_cash}
          onChange={(e) =>
            setForm({ ...form, starting_cash: Number(e.target.value) })
          }
          className="w-32 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          placeholder="Capital"
        />
        <button className="rounded bg-emerald-600 px-4 py-1 font-medium hover:bg-emerald-500">
          Run backtest
        </button>
        {msg && <span className="text-sm text-sky-400">{msg}</span>}
      </form>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Backtests</h2>
          <button
            onClick={() => load()}
            className="rounded border border-neutral-700 px-2 py-1 text-sm hover:bg-neutral-800"
          >
            Refresh
          </button>
        </div>
        {items.map((b) => (
          <button
            key={b.id}
            onClick={() => open(b.id)}
            className="flex w-full items-center justify-between rounded border border-neutral-800 bg-neutral-900 px-4 py-2 text-left text-sm hover:bg-neutral-800"
          >
            <span>
              #{b.id} {b.type} {b.symbol} {b.timeframe}
            </span>
            <span className="text-neutral-500">{b.status}</span>
          </button>
        ))}
      </section>

      {selected && (
        <section className="space-y-3 rounded border border-neutral-800 bg-neutral-900 p-4">
          <h2 className="font-semibold">
            Backtest #{selected.id} — {selected.status}
          </h2>
          {selected.error && (
            <p className="text-sm text-red-400">{selected.error}</p>
          )}
          <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
            {Object.entries(selected.metrics).map(([k, v]) => (
              <div
                key={k}
                className="rounded border border-neutral-800 px-2 py-1"
              >
                <div className="text-neutral-500">{k}</div>
                <div>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
              </div>
            ))}
          </div>
          {Object.keys(selected.monte_carlo).length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-neutral-400">
                Monte Carlo
              </h3>
              <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
                {Object.entries(selected.monte_carlo).map(([k, v]) => (
                  <div
                    key={k}
                    className="rounded border border-neutral-800 px-2 py-1"
                  >
                    <div className="text-neutral-500">{k}</div>
                    <div>{v.toFixed(4)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

export default function BacktestPage() {
  return <RequireAuth>{() => <BacktestView />}</RequireAuth>;
}
