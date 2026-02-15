import Link from "next/link";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/upload", label: "Upload" },
  { href: "/documents", label: "Documents" },
  { href: "/review", label: "Review" },
];

export function Navigation() {
  return (
    <nav className="nav-links" aria-label="Primary">
      {NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href} className="nav-link">
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
