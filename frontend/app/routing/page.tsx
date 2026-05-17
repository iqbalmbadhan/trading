"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Alloc = { venue: string; qty: number; price: number };
type Quote = {
  filled_qty: number;
  unfilled_qty: number;
  est_avg_price: number;
  allocations: Alloc[];
};

function RoutingView() {
  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    side: "buy",
    qty: 1,
    per_venue_cap: 1000000,
  });
  const [quote, setQuote] = useState<Quote | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function run(path: "quote" | "execute") {
    setMsg(null);
    try {
      const res = await apiFetch<Quote>(`/api/v1/routing/${path}`, {
        method: "POST",
        body: JSON.stringify({
          symbol: form.symbol,
          side: form.side,
          qty: Number(form.qty),
          per_venue_cap: Number(form.per_venue_cap),
        }),
      });
      setQuote(res);
      if (path === "execute") setMsg("Executed across venues (paper).");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Request failed");
    }
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6 p-8">
      <h1 className="text-2xl font-bold">Smart Order Routing</h1>
      <p className="text-sm text-neutral-400">
        Splits an order across connected venues by best price. Execute is
        paper-only in this build.
      </p>

      <div className="flex flex-wrap items-end gap-3 rounded border border-neutral-800 bg-neutral-900 p-4">
        <input
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value })}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
        />
        <select
          value={form.side}
          onChange={(e) => setForm({ ...form, side: e.target.value })}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
        >
          <option value="buy">buy</option>
          <option value="sell">sell</option>
        </select>
        <input
          type="number"
          step="any"
          value={form.qty}
          onChange={(e) => setForm({ ...form, qty: Number(e.target.value) })}
          className="w-24 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
        />
        <button
          onClick={() => run("quote")}
          className="rounded border border-neutral-700 px-3 py-1 hover:bg-neutral-800"
        >
          Quote
        </button>
        <button
          onClick={() => run("execute")}
          className="rounded bg-emerald-600 px-3 py-1 font-medium hover:bg-emerald-500"
        >
          Execute (paper)
        </button>
      </div>

      {msg && <p className="text-sm text-sky-400">{msg}</p>}

      {quote && (
        <section className="space-y-2 rounded border border-neutral-800 bg-neutral-900 p-4 text-sm">
          <p>
            Filled {quote.filled_qty} (unfilled {quote.unfilled_qty}) · est avg{" "}
            {quote.est_avg_price?.toFixed(2)}
          </p>
          <table className="w-full text-left">
            <thead className="text-neutral-500">
              <tr>
                <th>Venue</th>
                <th>Qty</th>
                <th>Price</th>
              </tr>
            </thead>
            <tbody>
              {quote.allocations.map((a) => (
                <tr key={a.venue} className="border-t border-neutral-800">
                  <td>{a.venue}</td>
                  <td>{a.qty}</td>
                  <td>{a.price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}

export default function RoutingPage() {
  return <RequireAuth>{() => <RoutingView />}</RequireAuth>;
}
