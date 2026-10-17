import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";
import { themeBootstrap } from "@/lib/theme";
import { LearningConversationsProvider } from "@/features/learning/use-learning-conversations";
import "./globals.css";
import "katex/dist/katex.min.css";
import "./rich-response.css";
import "./math-activity.css";
import "./simulation.css";
import "./theme.css";
import "./discovery.css";
import "./brand.css";
import "./profile.css";

const brandFont = localFont({ src: "./fonts/TiltWarp-Regular.ttf", weight: "400", style: "normal", display: "swap", variable: "--font-brand" });

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", interactiveWidget: "resizes-content" };

export const metadata: Metadata = {
  title: "Fliplecture — Ask FLAME anything",
  description: "Ask, learn and discover books, kits, teachers and classes with Fliplecture and FLAME.",
  icons: { icon: { url: "/brand/fliplecture-symbol.svg", type: "image/svg+xml" } },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={brandFont.variable} suppressHydrationWarning>
      <head><script id="flame-theme" dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
      <body><LearningConversationsProvider live={Boolean(process.env.FLAME_BFF_SHARED_KEY || process.env.NODE_ENV === "production")}>{children}</LearningConversationsProvider></body>
    </html>
  );
}
