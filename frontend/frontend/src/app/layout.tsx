import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { BackToTop } from "@/components/ui/layout/BackToTop";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: 'Predix',
    template: '%s · Predix',
  },
  description:
    'Observatorio de datos de empleo, educación y tendencias para Argentina, Chile y Uruguay.',
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-canvas text-body">
        {children}
        <BackToTop />
      </body>
    </html>
  );
}
