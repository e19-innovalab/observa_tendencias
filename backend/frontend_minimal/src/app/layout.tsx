import type { Metadata } from 'next';
import { Geist_Mono, Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ variable: '--font-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'Observa Tendencias', template: '%s · Observa Tendencias' },
  description:
    'Observatorio de tendencias laborales y educativas de Argentina, Chile y Uruguay: indicadores, ocupaciones, habilidades y proyecciones con datos oficiales.',
};

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="es" className={`${inter.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-canvas text-body">{children}</body>
    </html>
  );
}
