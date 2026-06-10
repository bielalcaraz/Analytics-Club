import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dataplant — Analítica industrial",
  description: "Transforma tus Excels en dashboards de KPIs industriales",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
