import { Suspense } from "react";
import { CatalogueSearch } from "@/features/discovery/catalogue-search";
export default function SearchPage() {
  return <Suspense fallback={<main className="discovery"><p role="status">Opening search…</p></main>}><CatalogueSearch /></Suspense>;
}
