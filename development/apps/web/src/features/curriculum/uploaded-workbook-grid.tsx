"use client";

import { useEffect, useState } from "react";

type SourceRow = { sheet: string; row_number: number; values: string[] };
type SourcePage = { items: SourceRow[]; total: number; next_offset: number | null;
  workbook_codes: string[]; expected_code: string };
const fields = ["Level", "Subject", "Domain", "Category", "Topic", "Subtopic"];

export function UploadedWorkbookGrid({ importId }: { importId: string }) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<SourcePage | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { setOffset(0); }, [importId]);
  useEffect(() => {
    let active = true;
    setPage(null); setError("");
    fetch("/api/b4/admin/curriculum/imports/" + importId + "/source-rows?offset=" + offset + "&limit=100",
      { cache: "no-store" }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error?.message || "Could not load workbook rows.");
      if (active) setPage(data);
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Could not load workbook rows."); });
    return () => { active = false; };
  }, [importId, offset]);
  const mismatched = page?.workbook_codes.filter(code =>
    code.trim().toLocaleLowerCase() !== page.expected_code.trim().toLocaleLowerCase()) ?? [];
  return <div className="admin-grid admin-import-source">
    {mismatched.length > 0 && <p className="b4-notice b4-notice-error" role="alert">
      This workbook contains Curriculum Code {mismatched.join(", ")}, but this curriculum uses {page?.expected_code}.
      To import these rows here, change the Curriculum Code column in Excel to {page?.expected_code}, then upload the corrected workbook.
    </p>}
    {!page && !error && <p role="status">Loading uploaded workbook rows…</p>}
    {error && <p className="b4-notice b4-notice-error" role="alert">{error}</p>}
    {page && <><p className="admin-help">Showing {offset + 1}–{Math.min(offset + 100, page.total)} of {page.total} uploaded rows. These rows are not yet in the saved draft.</p>
      <div className="admin-grid-scroll" role="region" aria-label="Uploaded Excel rows" tabIndex={0}>
        <table className="admin-grid-table"><thead><tr><th>Sheet</th><th>Excel row</th>
          {fields.map(field => <th key={field}>{field}</th>)}
        </tr></thead><tbody>{page.items.map(row => <tr key={row.sheet + ":" + row.row_number}>
          <td>{row.sheet}</td><td>{row.row_number}</td>
          {fields.map((field, index) => <td key={field}>{row.values[index + 1] || "—"}</td>)}
        </tr>)}</tbody></table>
      </div>
      {page.total > 0 && <nav className="admin-pagination" aria-label="Uploaded row pages">
        <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Previous</button>
        <span>{offset + 1}–{Math.min(offset + 100, page.total)} of {page.total}</span>
        <button disabled={page.next_offset === null} onClick={() => setOffset(offset + 100)}>Next</button>
      </nav>}
    </>}
  </div>;
}
