import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { themeBootstrap } from "@/lib/theme";
import "./globals.css";
import "katex/dist/katex.min.css";
import "./rich-response.css";
import "./math-activity.css";
import "./simulation.css";
import "./theme.css";

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", interactiveWidget: "resizes-content" };

export const metadata: Metadata = {
  title: "FLAME",
  description: "FLAME — a student learning workspace by FlipLecture",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script id="flame-theme" dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
      <body>{children}</body>
    </html>
  );
}
