"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

type AppNavProps = {
  className?: string;
};

const links = [
  { href: "/watchlist", label: "Watchlist", tone: "normal" },
  { href: "/dashboard", label: "Dashboard", tone: "normal" },
  { href: "/paper", label: "Paper", tone: "normal" },
  { href: "/accuracy", label: "Accuracy", tone: "normal" },
  { href: "/admin", label: "Admin", tone: "muted" }
] as const;

export default function AppNav({ className }: AppNavProps) {
  const router = useRouter();

  function goBack() {
    if (window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/watchlist");
  }

  return (
    <nav className={className ?? "link-row"} aria-label="Primary navigation">
      <button className="back-button" onClick={goBack} type="button">
        ← Back
      </button>
      {links.map((link) => (
        <Link
          className={link.tone === "muted" ? "text-link nav-muted" : "text-link"}
          href={link.href}
          key={link.href}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
