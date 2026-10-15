import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rumbo · Observatorio laboral y educativo",
  description: "Tendencias laborales y educativas del Cono Sur (Argentina, Uruguay y Chile).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
