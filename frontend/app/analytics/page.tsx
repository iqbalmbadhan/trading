"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Metrics = {
  backtests: number;
  best_sharpe?: number;
  best_type?: string;
  best_backtest_id?: number;
};
type Row = {
  type: string;
  backtests: number;
  sharpe: number;
  sortino: number;
  calmar: number;
  total_return: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  max_drawdown: number;
};

function AnalyticsView() {
  const [m, setM] = useState<Metrics | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setM(await apiFetch<Metrics>("/api/v1/analytics/metrics"));
    setRows(await apiFetch<Row[]>("/api/v1/analytics/strategy-comparison"));
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, [load]);

  if (err) return <p className="p-8 text-red-400">{err}</p>;
  if (!m) return <p className="p-8 text-neutral-500">Loading…</p>;

  const cols: (keyof Row)[] = [
    "sharpe",
    "sortino",
    "calmar",
    "total_return",
    "win_rate",
    "profit_factor",
    "expectancy",
    "max_drawdown",
  ];

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Analytics</h1>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded border border-neutral-800 bg-neutral-900 p-3">
          <div className="text-neutral-500">Backtests</div>
          <div className="text-xl">{m.backtests}</div>
        </div>
        <div className="rounded border border-neutral-800 bg-neutral-900 p-3">
          <div className="text-neutral-500">Best Sharpe</div>
          <div className="text-xl">
            {m.best_sharpe !== undefined ? m.best_sharpe.toFixed(2) : "—"}
          </div>
        </div>
        <div className="rounded border border-neutral-800 bg-neutral-900 p-3">
          <div className="text-neutral-500">Best strategy</div>
          <div className="text-xl">{m.best_type ?? "—"}</div>
        </div>
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Per-strategy comparison</h2>
        {rows.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No finished backtests yet. Run one from the Backtest page.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-neutral-500">
              <tr>
                <th className="py-1">Type</th>
                <th>#</th>
                {cols.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.type} className="border-t border-neutral-800">
                  <td className="py-1">{r.type}</td>
                  <td>{r.backtests}</td>
                  {cols.map((c) => (
                    <td key={c}>{(r[c] as number).toFixed(3)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

export default function AnalyticsPage() {
  return <RequireAuth>{() => <AnalyticsView />}</RequireAuth>;
}
