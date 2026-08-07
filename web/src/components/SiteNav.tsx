"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "What it is" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/investigate", label: "Investigate" },
];

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="mx-auto flex w-full max-w-[1180px] items-center justify-between px-5 pt-5 md:px-8">
      <Link href="/" className="display text-2xl tracking-tight text-[var(--ink)]">
        CUNCT
      </Link>
      <nav className="flex items-center gap-1 sm:gap-2">
        {LINKS.map((l) => {
          const active = pathname === l.href;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`mono px-3 py-1.5 text-[11px] uppercase tracking-[0.14em] transition ${
                active
                  ? "text-[var(--signal-deep)] underline underline-offset-8"
                  : "text-[var(--mute)] hover:text-[var(--ink)]"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
