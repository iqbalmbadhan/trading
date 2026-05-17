"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Holding = {
  symbol: string;
  base: string;
  qty: number;
  price_usd: number;
  value_usd: number;
  is_paper: boolean;
};
type Summary = {
  total_value_usd: number;
  holdings: Holding[];
  allocation: Record<string, number>;
  exposure_by_base: Record<string, number>;
};
type Matrix = Record<string, Record<string, number | null>>;

function PortfolioView() {
  const [s, setS] = useState<Summary | null>(null);
  const [matrix, setMatrix] = useState<Matrix>({});
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setS(await apiFetch<Summary>("/api/v1/portfolio/summary"));
    setMatrix(
      (await apiFetch<{ matrix: Matrix }>("/api/v1/portfolio/correlation"))
        .matrix,
    );
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, [load]);

  if (err) return <p className="p-8 text-red-400">{err}</p>;
  if (!s) return <p className="p-8 text-neutral-500">Loading…</p>;

  const symbols = Object.keys(matrix);
  const cell = (v: number | null) => {
    if (v === null) return "text-neutral-600";
    return v >= 0 ? "text-black" : "text-white";
  };

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Portfolio</h1>
      <p className="text-lg">
        Total value:{" "}
        <span className="font-mono text-emerald-400">
          ${s.total_value_usd.toFixed(2)}
        </span>
      </p>

      <section>
        <h2 className="mb-2 font-semibold">Holdings</h2>
        <table className="w-full text-left text-sm">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1">Symbol</th>
              <th>Qty</th>
              <th>Price USD</th>
              <th>Value USD</th>
              <th>Alloc</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            {s.holdings.map((h) => (
              <tr key={h.symbol} className="border-t border-neutral-800">
                <td className="py-1">{h.symbol}</td>
                <td>{h.qty}</td>
                <td>{h.price_usd.toFixed(2)}</td>
                <td>{h.value_usd.toFixed(2)}</td>
                <td>{((s.allocation[h.symbol] ?? 0) * 100).toFixed(1)}%</td>
                <td>{h.is_paper ? "paper" : "live"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Exposure by asset</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(s.exposure_by_base).map(([b, v]) => (
            <span
              key={b}
              className="rounded border border-neutral-800 bg-neutral-900 px-3 py-1 text-sm"
            >
              {b}: {(v * 100).toFixed(1)}%
            </span>
          ))}
        </div>
      </section>

      {symbols.length > 0 && (
        <section>
          <h2 className="mb-2 font-semibold">Correlation matrix</h2>
          <table className="text-xs">
            <thead>
              <tr>
                <th className="p-1"></th>
                {symbols.map((c) => (
                  <th key={c} className="p-1 text-neutral-500">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {symbols.map((r) => (
                <tr key={r}>
                  <td className="p-1 text-neutral-500">{r}</td>
                  {symbols.map((c) => {
                    const v = matrix[r][c];
                    return (
                      <td
                        key={c}
                        className={`p-1 text-center ${cell(v)}`}
                        style={{
                          background:
                            v === null
                              ? "#262626"
                              : v >= 0
                                ? `rgba(52,211,153,${Math.abs(v)})`
                                : `rgba(248,113,113,${Math.abs(v)})`,
                        }}
                      >
                        {v === null ? "—" : v.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}

export default function PortfolioPage() {
  return <RequireAuth>{() => <PortfolioView />}</RequireAuth>;
}
