"use client";
import { useEffect, useRef, useState } from "react";
import { b9Get } from "@/lib/api/b9-client";

export function useCatalogue<T>(route: string, hideDuringRefresh = false) {
  const [data, setData] = useState<{key:string;rows:T[];total:number}|null>(null);
  const [search, setRawSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(hideDuringRefresh);
  const [error, setError] = useState("");
  const limit = 30;
  const query = new URLSearchParams({ q: search, offset: String(offset), limit: String(limit) });
  for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
  const queryKey=route+"?"+query;
  const currentQuery=useRef(queryKey);currentQuery.current=queryKey;
  const requestSequence = useRef(0);
  const setSearch = (value: string) => { setRawSearch(value); setOffset(0); };
  const setFilter = (key: string, value: string) => {
    setFilters(previous => ({ ...previous, [key]: value })); setOffset(0);
  };
  async function refresh() {
    const request = ++requestSequence.current;
    const requestedQuery=currentQuery.current;
    setLoading(true); setError("");
    try {
      const result = await b9Get<{ items: T[]; total: number }>(requestedQuery);
      if (request === requestSequence.current && requestedQuery===currentQuery.current) { setData({key:requestedQuery,rows:result.items,total:result.total}); }
    } catch (cause) { if (request === requestSequence.current) setError(cause instanceof Error ? cause.message : "Catalogue unavailable."); }
    finally { if (request === requestSequence.current) setLoading(false); }
  }
  useEffect(() => { void refresh(); return () => { requestSequence.current++; }; }, [route, search, offset, filters]);
  const refreshing=hideDuringRefresh?(loading||(!error&&data?.key!==queryKey)):loading;
  const visible=!hideDuringRefresh||(!refreshing&&!error&&data?.key===queryKey);
  const rows=visible?data?.rows??[]:[];
  const total=visible?data?.total??0:0;
  return { rows, search, setSearch, filters, setFilter, offset, setOffset, total, limit,
    loading:refreshing, error, setError, refresh };
}

export function ListPages({ listing }: { listing: { offset: number; total: number; limit: number;
  setOffset: (value: number) => void; loading: boolean } }) {
  if (listing.total <= listing.limit) return null;
  return <nav className="b9-pages" aria-label="Catalogue pages">
    <button disabled={listing.loading || listing.offset === 0}
      onClick={() => listing.setOffset(Math.max(0, listing.offset - listing.limit))}>Previous</button>
    <span>{listing.offset + 1}–{Math.min(listing.total, listing.offset + listing.limit)} of {listing.total}</span>
    <button disabled={listing.loading || listing.offset + listing.limit >= listing.total}
      onClick={() => listing.setOffset(listing.offset + listing.limit)}>Next</button>
  </nav>;
}

