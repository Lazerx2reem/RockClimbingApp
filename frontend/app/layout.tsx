import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ascent",
  description: "Training logs, send tracking, and AI-powered climbing analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
