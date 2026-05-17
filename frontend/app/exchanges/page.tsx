"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Account = {
  id: number;
  exchange: string;
  label: string;
  permissions_verified: boolean;
  is_active: boolean;
};

function ExchangesView() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState({
    exchange: "binance",
    label: "",
    api_key: "",
    secret: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setAccounts(await apiFetch<Account[]>("/api/v1/exchanges"));
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  async function connect(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch<Account>("/api/v1/exchanges/connect", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setForm({ ...form, label: "", api_key: "", secret: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect(id: number) {
    await apiFetch(`/api/v1/exchanges/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Exchanges</h1>

      <div className="rounded border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-300">
        API keys must be <strong>trade-only</strong>. Keys with withdrawal
        permission are rejected automatically. Keys are stored
        envelope-encrypted at rest.
      </div>

      <section className="space-y-3">
        <h2 className="font-semibold">Connected accounts</h2>
        {accounts.length === 0 && (
          <p className="text-sm text-neutral-500">No exchanges connected.</p>
        )}
        <ul className="space-y-2">
          {accounts.map((a) => (
            <li
              key={a.id}
              className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-900 px-4 py-3"
            >
              <span>
                <span className="font-medium">{a.label}</span>{" "}
                <span className="text-neutral-500">({a.exchange})</span>
                {a.permissions_verified && (
                  <span className="ml-2 text-xs text-emerald-400">
                    trade-only verified
                  </span>
                )}
              </span>
              <button
                onClick={() => disconnect(a.id)}
                className="rounded border border-neutral-700 px-3 py-1 text-sm hover:bg-neutral-800"
              >
                Disconnect
              </button>
            </li>
          ))}
        </ul>
      </section>

      <form
        onSubmit={connect}
        className="space-y-3 rounded border border-neutral-800 bg-neutral-900 p-4"
      >
        <h2 className="font-semibold">Connect a new exchange</h2>
        <input
          required
          placeholder="Exchange id (e.g. binance)"
          value={form.exchange}
          onChange={(e) => setForm({ ...form, exchange: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        <input
          required
          placeholder="Label"
          value={form.label}
          onChange={(e) => setForm({ ...form, label: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        <input
          required
          placeholder="API key"
          value={form.api_key}
          onChange={(e) => setForm({ ...form, api_key: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        <input
          required
          type="password"
          placeholder="API secret"
          value={form.secret}
          onChange={(e) => setForm({ ...form, secret: e.target.value })}
          className="w-full rounded border border-neutral-700 bg-neutral-950 px-3 py-2"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "Verifying…" : "Connect"}
        </button>
      </form>
    </main>
  );
}

export default function ExchangesPage() {
  return <RequireAuth>{() => <ExchangesView />}</RequireAuth>;
}
