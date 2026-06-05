import Link from "next/link";

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
  return (
    <nav className={className ?? "link-row"} aria-label="Primary navigation">
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
