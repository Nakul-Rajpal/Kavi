import type { Metadata } from "next";
import "../styles/globals.css";
import "leaflet/dist/leaflet.css";

export const metadata: Metadata = {
  title: "Kavi | Autonomous City Repair",
  description: "Drone-based infrastructure detection and repair management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
