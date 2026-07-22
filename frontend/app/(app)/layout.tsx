"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/token";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/logbook", label: "Logbook" },
  { href: "/sessions", label: "Sessions" },
];

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-stone-400">Loading…</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link href="/dashboard" className="text-lg font-bold text-emerald-800">
            Ascent
          </Link>
          <div className="flex gap-1">
            {NAV_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  pathname.startsWith(href)
                    ? "bg-emerald-50 text-emerald-800"
                    : "text-stone-600 hover:bg-stone-100"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          <button
            onClick={() => {
              clearToken();
              router.replace("/login");
            }}
            className="ml-auto rounded-md px-3 py-1.5 text-sm text-stone-500 hover:bg-stone-100"
          >
            Log out
          </button>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
