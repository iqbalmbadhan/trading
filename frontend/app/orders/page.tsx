"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

const PHRASE = "I UNDERSTAND I CAN LOSE MONEY";

type Order = {
  id: number;
  symbol: string;
  side: string;
  type: string;
  qty: number;
  price: number | null;
  status: string;
  filled_qty: number;
  avg_fill: number | null;
  fees: number;
  slippage_bps: number | null;
  is_paper: boolean;
};

type Position = {
  id: number;
  symbol: string;
  side: string;
  qty: number;
  avg_entry: number;
  is_paper: boolean;
};

type LiveStatus = { live_trading_enabled: boolean };

function OrdersView() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [live, setLive] = useState<LiveStatus>({ live_trading_enabled: false });
  const [phrase, setPhrase] = useState("");
  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    side: "buy",
    qty: 1,
    stop_price: 0,
  });
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setOrders(await apiFetch<Order[]>("/api/v1/orders"));
    setPositions(await apiFetch<Position[]>("/api/v1/positions"));
    setLive(await apiFetch<LiveStatus>("/api/v1/account/live-trading"));
  }, []);

  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, [refresh]);

  async function enableLive() {
    try {
      await apiFetch("/api/v1/account/live-trading", {
        method: "POST",
        body: JSON.stringify({ confirm_phrase: phrase }),
      });
      setPhrase("");
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Enable failed");
    }
  }

  async function placeOrder(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await apiFetch("/api/v1/orders/manual-place", {
        method: "POST",
        body: JSON.stringify({
          symbol: form.symbol,
          side: form.side,
          qty: Number(form.qty),
          stop_price: Number(form.stop_price) || null,
        }),
      });
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Order failed");
    }
  }

  async function closePosition(id: number) {
    await apiFetch(`/api/v1/positions/${id}/close`, { method: "DELETE" });
    await refresh();
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Orders &amp; Trades</h1>

      <section
        className={`rounded border p-3 text-sm ${live.live_trading_enabled ? "border-red-700 bg-red-950/40 text-red-300" : "border-sky-800 bg-sky-950/40 text-sky-300"}`}
      >
        {live.live_trading_enabled ? (
          <span>
            Live trading is ENABLED. Orders without “live” are still paper.
          </span>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <span>Paper mode. To enable live, type the exact phrase:</span>
            <code className="rounded bg-neutral-800 px-1">{PHRASE}</code>
            <input
              value={phrase}
              onChange={(e) => setPhrase(e.target.value)}
              className="flex-1 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
            />
            <button
              onClick={enableLive}
              className="rounded bg-red-600 px-3 py-1 hover:bg-red-500"
            >
              Enable live
            </button>
          </div>
        )}
      </section>

      <form
        onSubmit={placeOrder}
        className="flex flex-wrap items-end gap-3 rounded border border-neutral-800 bg-neutral-900 p-4"
      >
        <input
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value })}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          placeholder="Symbol"
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
          placeholder="Qty"
        />
        <input
          type="number"
          step="any"
          value={form.stop_price}
          onChange={(e) =>
            setForm({ ...form, stop_price: Number(e.target.value) })
          }
          className="w-28 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          placeholder="Stop"
        />
        <button className="rounded bg-emerald-600 px-4 py-1 font-medium hover:bg-emerald-500">
          Place (paper)
        </button>
        {msg && <span className="text-sm text-red-400">{msg}</span>}
      </form>

      <section>
        <h2 className="mb-2 font-semibold">Open positions</h2>
        {positions.length === 0 && (
          <p className="text-sm text-neutral-500">No positions.</p>
        )}
        {positions.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between border-b border-neutral-800 py-2 text-sm"
          >
            <span>
              {p.symbol} {p.side} {p.qty} @ {p.avg_entry}
            </span>
            <button
              onClick={() => closePosition(p.id)}
              className="rounded border border-neutral-700 px-2 py-1 hover:bg-neutral-800"
            >
              Close
            </button>
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Orders</h2>
        <table className="w-full text-left text-sm">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1">Symbol</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Status</th>
              <th>Avg fill</th>
              <th>Slippage bps</th>
              <th>Fees</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-t border-neutral-800">
                <td className="py-1">{o.symbol}</td>
                <td>{o.side}</td>
                <td>{o.qty}</td>
                <td>{o.status}</td>
                <td>{o.avg_fill ?? "—"}</td>
                <td>{o.slippage_bps?.toFixed(2) ?? "—"}</td>
                <td>{o.fees}</td>
                <td>{o.is_paper ? "paper" : "live"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

export default function OrdersPage() {
  return <RequireAuth>{() => <OrdersView />}</RequireAuth>;
}
