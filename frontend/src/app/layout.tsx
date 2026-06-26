import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "chart-fights | 1v1 me in stocks",
  description: "Psychological 1v1 chart PvP on accelerated historical market data. Tempo fights, sabotage, voice trash-talk.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#0a0c10] text-[#e5e7eb]">
        {children}
      </body>
    </html>
  );
}
