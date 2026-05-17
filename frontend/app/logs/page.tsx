"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch } from "@/lib/api";

type Audit = {
  id: number;
  ts: string;
  actor: string;
  action: string;
  target: string;
  before: unknown;
  after: unknown;
};
type Decision = {
  id: number;
  ts: number;
  symbol: string;
  decision: string;
  reasoning: Record<string, unknown>;
  indicators: Record<string, unknown>;
};

function LogsView() {
  const [audit, setAudit] = useState<Audit[]>([]);
  const [actionFilter, setActionFilter] = useState("");
  const [runId, setRunId] = useState("");
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const loadAudit = useCallback(async () => {
    const q = actionFilter ? `?action=${encodeURIComponent(actionFilter)}` : "";
    setAudit(await apiFetch<Audit[]>(`/api/v1/audit${q}`));
  }, [actionFilter]);

  useEffect(() => {
    loadAudit().catch((e) => setMsg(e.message));
  }, [loadAudit]);

  async function loadDecisions() {
    setMsg(null);
    if (!runId) return;
    try {
      setDecisions(
        await apiFetch<Decision[]>(`/api/v1/audit/decisions/${runId}`),
      );
    } catch (e) {
      setDecisions([]);
      setMsg(e instanceof Error ? e.message : "Not found");
    }
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">Logs &amp; Audit</h1>

      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">Audit log</h2>
          <input
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            placeholder="filter by action (e.g. kill_switch.trip)"
            className="flex-1 rounded border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm"
          />
        </div>
        <table className="w-full text-left text-xs">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1">Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {audit.map((a) => (
              <tr key={a.id} className="border-t border-neutral-800">
                <td className="py-1">{a.ts}</td>
                <td>{a.actor}</td>
                <td>{a.action}</td>
                <td>{a.target}</td>
                <td className="font-mono">
                  {JSON.stringify(a.after ?? a.before ?? {})}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {audit.length === 0 && (
          <p className="text-sm text-neutral-500">No audit entries.</p>
        )}
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">Strategy decisions</h2>
          <input
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            placeholder="strategy run id"
            className="w-40 rounded border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm"
          />
          <button
            onClick={loadDecisions}
            className="rounded border border-neutral-700 px-3 py-1 text-sm hover:bg-neutral-800"
          >
            Load
          </button>
        </div>
        {msg && <p className="text-sm text-red-400">{msg}</p>}
        {decisions.map((d) => (
          <div
            key={d.id}
            className="rounded border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs"
          >
            <span className="text-neutral-300">
              {d.symbol} → {d.decision}
            </span>{" "}
            <span className="text-neutral-500">
              indicators {JSON.stringify(d.indicators)} ·{" "}
              {JSON.stringify(d.reasoning)}
            </span>
          </div>
        ))}
      </section>
    </main>
  );
}

export default function LogsPage() {
  return <RequireAuth>{() => <LogsView />}</RequireAuth>;
}
