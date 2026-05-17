"use client";

import { useRouter } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { clearTokens } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <RequireAuth>
      {(user) => (
        <main className="flex min-h-screen flex-col items-center justify-center gap-4">
          <h1 className="text-3xl font-bold">Trading Bot Platform</h1>
          <p className="text-neutral-400">
            Signed in as <span className="text-neutral-200">{user.email}</span>
          </p>
          <p className="text-sm text-neutral-500">
            2FA {user.totp_enabled ? "enabled" : "not enabled"}
          </p>
          <button
            onClick={logout}
            className="rounded border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
          >
            Sign out
          </button>
        </main>
      )}
    </RequireAuth>
  );
}
