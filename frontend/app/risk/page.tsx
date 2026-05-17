"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type RiskConfig = {
  max_trade_risk_pct: number;
  max_position_value: number;
  max_open_positions: number;
  blacklist: string[];
  strategy_daily_loss_limit: number;
  account_daily_loss_limit: number;
  max_drawdown_pct: number;
  max_correlation: number;
  require_stop_loss: boolean;
};

type KsStatus = { active: boolean; reason: string | null };
type KsEvent = {
  id: number;
  reason: string;
  triggered_at: string;
  resolved_at: string | null;
};

const NUMERIC: (keyof RiskConfig)[] = [
  "max_trade_risk_pct",
  "max_position_value",
  "max_open_positions",
  "strategy_daily_loss_limit",
  "account_daily_loss_limit",
  "max_drawdown_pct",
  "max_correlation",
];

function RiskView() {
  const [cfg, setCfg] = useState<RiskConfig | null>(null);
  const [ks, setKs] = useState<KsStatus | null>(null);
  const [events, setEvents] = useState<KsEvent[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setCfg(await apiFetch<RiskConfig>("/api/v1/risk/rules"));
    setKs(await apiFetch<KsStatus>("/api/v1/risk/kill-switch-status"));
    setEvents(await apiFetch<KsEvent[]>("/api/v1/risk/kill-switch/events"));
  }, []);

  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, [refresh]);

  async function saveRules() {
    if (!cfg) return;
    try {
      await apiFetch("/api/v1/risk/rules", {
        method: "PUT",
        body: JSON.stringify(cfg),
      });
      setMsg("Rules saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function toggleKill() {
    if (!ks) return;
    const path = ks.active
      ? "/api/v1/risk/kill-switch/clear"
      : "/api/v1/risk/kill-switch";
    if (
      !ks.active &&
      !window.confirm(
        "Trip the global kill switch? This stops all strategies and blocks new orders.",
      )
    )
      return;
    await apiFetch(path, {
      method: "POST",
      body: JSON.stringify({ reason: "manual" }),
    });
    await refresh();
  }

  if (!cfg || !ks) {
    return <p className="p-8 text-neutral-500">Loading…</p>;
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Risk Management</h1>

      <section
        className={`rounded border p-4 ${ks.active ? "border-red-600 bg-red-950/40" : "border-neutral-800 bg-neutral-900"}`}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold">
              Kill switch: {ks.active ? "ACTIVE" : "inactive"}
            </p>
            {ks.reason && (
              <p className="text-sm text-neutral-400">reason: {ks.reason}</p>
            )}
          </div>
          <button
            onClick={toggleKill}
            className={`rounded px-4 py-2 font-medium ${ks.active ? "bg-neutral-700 hover:bg-neutral-600" : "bg-red-600 hover:bg-red-500"}`}
          >
            {ks.active ? "Clear" : "Trip kill switch"}
          </button>
        </div>
      </section>

      <section className="space-y-3 rounded border border-neutral-800 bg-neutral-900 p-4">
        <h2 className="font-semibold">Global rules</h2>
        {NUMERIC.map((k) => (
          <label key={k} className="flex items-center justify-between gap-4">
            <span className="text-sm text-neutral-400">{k}</span>
            <input
              type="number"
              step="any"
              value={cfg[k] as number}
              onChange={(e) => setCfg({ ...cfg, [k]: Number(e.target.value) })}
              className="w-40 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
            />
          </label>
        ))}
        <label className="flex items-center justify-between">
          <span className="text-sm text-neutral-400">require_stop_loss</span>
          <input
            type="checkbox"
            checked={cfg.require_stop_loss}
            onChange={(e) =>
              setCfg({ ...cfg, require_stop_loss: e.target.checked })
            }
          />
        </label>
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm text-neutral-400">
            blacklist (comma-separated)
          </span>
          <input
            value={cfg.blacklist.join(",")}
            onChange={(e) =>
              setCfg({
                ...cfg,
                blacklist: e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
            className="w-60 rounded border border-neutral-700 bg-neutral-950 px-2 py-1"
          />
        </label>
        {msg && <p className="text-sm text-sky-400">{msg}</p>}
        <button
          onClick={saveRules}
          className="rounded bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500"
        >
          Save rules
        </button>
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">Kill switch history</h2>
        {events.length === 0 && (
          <p className="text-sm text-neutral-500">No events.</p>
        )}
        {events.map((e) => (
          <div
            key={e.id}
            className="rounded border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm"
          >
            <span className="text-neutral-300">{e.reason}</span>{" "}
            <span className="text-neutral-500">
              triggered {e.triggered_at}
              {e.resolved_at ? ` · resolved ${e.resolved_at}` : " · unresolved"}
            </span>
          </div>
        ))}
      </section>
    </main>
  );
}

export default function RiskPage() {
  return <RequireAuth>{() => <RiskView />}</RequireAuth>;
}
