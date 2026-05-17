"use client";

import { RequireAuth } from "@/components/RequireAuth";

export default function Home() {
  return (
    <RequireAuth>
      {(user) => (
        <main className="space-y-3 p-8">
          <h1 className="text-2xl font-bold">Overview</h1>
          <p className="text-neutral-400">
            Signed in as <span className="text-neutral-200">{user.email}</span>
          </p>
          <p className="text-sm text-neutral-500">
            2FA {user.totp_enabled ? "enabled" : "not enabled"}
          </p>
          <p className="text-sm text-neutral-500">
            Use the navigation above to manage strategies, run backtests, review
            the portfolio, and configure risk and alerts. All trading defaults
            to paper mode.
          </p>
        </main>
      )}
    </RequireAuth>
  );
}
