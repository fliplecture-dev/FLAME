export const catalogues = [
  { id: "books", label: "Books" }, { id: "kits", label: "Kits" },
  { id: "teachers", label: "Teachers" }, { id: "classes", label: "Classes" },
] as const;
export type CatalogueKind = typeof catalogues[number]["id"];
export function catalogueKind(value: unknown): CatalogueKind {
  return catalogues.some(item => item.id === value) ? value as CatalogueKind : "books";
}
export type CatalogueItem = {
  id: string; kind: CatalogueKind; version: number; title: string; description: string | null;
  category: string | null; subject: string | null; language: string | null; level: string | null;
  format: string | null; author: string | null; availability: string | null; location: string | null;
  price: string | null; currency: string | null; schedule: string | null;
  languages?: string[];
};
export const filterLabels: Record<string, string> = { category: "Category", subject: "Subject", level: "Grade / Age", language: "Language", format: "Format", author: "Author", location: "Location" };
export type CatalogueResults = { items: CatalogueItem[]; total: number; inventory_total: number; offset: number; limit: number; facets: Record<string, string[]> };
export function searchHref(kind: CatalogueKind, query = "") {
  const params = new URLSearchParams({ kind });
  if (query.trim()) params.set("q", query.trim().slice(0, 200));
  return `/search?${params}`;
}
