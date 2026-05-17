"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { clearTokens } from "@/lib/api";

const NAV: { href: string; label: string }[] = [
  { href: "/", label: "Overview" },
  { href: "/strategies", label: "Strategies" },
  { href: "/backtest", label: "Backtest" },
  { href: "/orders", label: "Orders" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/analytics", label: "Analytics" },
  { href: "/risk", label: "Risk" },
  { href: "/routing", label: "Routing" },
  { href: "/exchanges", label: "Exchanges" },
  { href: "/alerts", label: "Alerts" },
  { href: "/logs", label: "Logs" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-neutral-800 bg-neutral-950/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <button
            className="flex items-center gap-2 font-semibold"
            onClick={() => router.push("/")}
          >
            <span className="text-emerald-400">▲</span> TradingBot
          </button>
          <nav className="hidden gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`rounded px-2 py-1 text-sm ${
                  pathname === n.href
                    ? "bg-neutral-800 text-white"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                {n.label}
              </Link>
            ))}
            <button
              onClick={logout}
              className="ml-2 rounded border border-neutral-700 px-2 py-1 text-sm hover:bg-neutral-800"
            >
              Sign out
            </button>
          </nav>
          <button
            className="rounded border border-neutral-700 px-2 py-1 text-sm md:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            ☰
          </button>
        </div>
        {open && (
          <nav className="grid grid-cols-2 gap-1 border-t border-neutral-800 px-4 py-2 md:hidden">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                onClick={() => setOpen(false)}
                className={`rounded px-2 py-2 text-sm ${
                  pathname === n.href
                    ? "bg-neutral-800 text-white"
                    : "text-neutral-400"
                }`}
              >
                {n.label}
              </Link>
            ))}
            <button
              onClick={logout}
              className="rounded border border-neutral-700 px-2 py-2 text-sm"
            >
              Sign out
            </button>
          </nav>
        )}
      </header>
      <div className="mx-auto max-w-5xl">{children}</div>
    </div>
  );
}
