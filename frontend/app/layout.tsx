import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Navigation } from "../components/nav";

export const metadata: Metadata = {
  title: "svanDoc",
  description: "Upload, review, and export invoice and receipt data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <div className="topbar-inner">
              <div>
                <div className="brand">svanDoc</div>
                <div className="brand-note">MVP app shell (auth-ready)</div>
              </div>
              <Navigation />
            </div>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
