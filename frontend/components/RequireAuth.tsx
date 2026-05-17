"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, clearTokens, getAccessToken } from "@/lib/api";

export type CurrentUser = {
  id: number;
  email: string;
  role: string;
  totp_enabled: boolean;
};

export function RequireAuth({
  children,
}: {
  children: (user: CurrentUser) => React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    apiFetch<CurrentUser>("/api/v1/auth/me")
      .then(setUser)
      .catch(() => {
        clearTokens();
        router.replace("/login");
      });
  }, [router]);

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center text-neutral-500">
        Loading…
      </main>
    );
  }
  return <>{children(user)}</>;
}
