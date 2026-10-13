"use client";
import { createContext, useContext } from "react";
export type ExploreKind = "resource" | "tutor" | "kit";
export const ExploreContext = createContext<{ fromAnswer: (sessionId: string, messageId: string, kind?: ExploreKind, highlight?: string) => Promise<void> } | null>(null);
export const useExplore = () => useContext(ExploreContext);
