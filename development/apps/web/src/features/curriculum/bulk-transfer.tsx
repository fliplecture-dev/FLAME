"use client";
import { useEffect, useRef, useState } from "react";
import { B9Error, b9Get, b9Mutation } from "@/lib/api/b9-client";
import { uploadPrivateFile, privateExport } from "@/lib/api/private-transfers";

type Kind = "resources" | "teachers" | "students" | "activity-kits";
type Job = { id:string; filename:string; status:string; preview_token:string; total:number; counts:Record<string,number>;
  rows:{row:number;record_key:string;name:string;operation:string;existing_id?:string|null;errors:string[];preserved_fields:string[];fields_to_fill:string[];mappings_to_add:number}[];
  result?:{added:number;merged:number;unchanged:number;mappings_added:number}|null };
export function BulkTransfer({ kind, onImported }: { kind:Kind; onImported:()=>void|Promise<void> }) {
  const [open,setOpen]=useState(false),[file,setFile]=useState<File|null>(null),[job,setJob]=useState<Job|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[page,setPage]=useState(0),[confirmed,setConfirmed]=useState(false);
  const guard=useRef(false),dialog=useRef<HTMLDialogElement>(null),opener=useRef<HTMLElement|null>(null);
  const storageKey="flame-bulk-import-"+kind;
  useEffect(()=>{if(open){opener.current=document.activeElement as HTMLElement;dialog.current?.showModal();}else{dialog.current?.close();opener.current?.focus();}},[open]);
  function remember(value:Job|null){
    if(value){
      if(!Array.isArray(value.rows)||!value.counts)throw new Error("Import response could not be displayed. Refresh the current import status before retrying; completion could not be confirmed.");
      const rows=value.rows.map(row=>({...row,errors:Array.isArray(row.errors)?row.errors:row.operation==="invalid"?["This row is invalid. Review the latest comparison for details."]:[],preserved_fields:Array.isArray(row.preserved_fields)?row.preserved_fields:[],fields_to_fill:Array.isArray(row.fields_to_fill)?row.fields_to_fill:[],mappings_to_add:row.mappings_to_add??0}));
      value={...value,rows,counts:{...value.counts,invalid:Math.max(value.counts.invalid??0,rows.filter(row=>row.operation==="invalid").length)}};
    }
    setJob(value);setConfirmed(false);setPage(0);if(value?.status==="review")localStorage.setItem(storageKey,value.id);else localStorage.removeItem(storageKey);}
  async function act(task:()=>Promise<void>){if(guard.current)return;guard.current=true;setBusy(true);setError("");try{await task();}catch(cause){setError((cause instanceof Error?cause.message:"Bulk transfer failed.")+(cause instanceof B9Error&&cause.reference?" Reference: "+cause.reference:""));}finally{guard.current=false;setBusy(false);}}
  async function show(){setOpen(true);setError("");const saved=localStorage.getItem(storageKey);if(saved&&!job)await act(async()=>{try{remember(await b9Get<Job>("admin/bulk/imports/"+saved));}catch(cause){if(cause instanceof B9Error&&cause.status===404)localStorage.removeItem(storageKey);else throw cause;}});}
  async function close(){if(guard.current)return;if(job?.status==="review"){if(!window.confirm("Cancel this import? No catalogue changes will be applied. Staged unused media will be removed."))return;await act(async()=>{remember(await b9Mutation<Job>("admin/bulk/imports/"+job.id+"/cancel","POST",{}));setOpen(false);});}else setOpen(false);}
  async function download(action:"template"|"export",packageFiles=false){await act(async()=>{
    const direct=await privateExport({purpose:"bulk",kind,action,package:packageFiles});
    if(direct){const url=URL.createObjectURL(direct.blob);const a=document.createElement("a");a.href=url;a.download=direct.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;}
    const result=await fetch(`/api/b9/admin/bulk/${kind}/${action}${packageFiles?"?package=true":""}`,{cache:"no-store"});
    if(!result.ok)throw new B9Error(await result.json(),result.status);
    const url=URL.createObjectURL(await result.blob());const a=document.createElement("a");a.href=url;a.download=kind+(action==="template"?"-template":"")+(packageFiles?".zip":".xlsx");a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });}
  async function preview(){if(!file)return;await act(async()=>{
    const direct=await uploadPrivateFile<Job>(file,{purpose:"bulk",kind});if(direct){remember(direct);return;}
    const csrf=await fetch("/api/auth/csrf",{cache:"no-store"}).then(r=>r.json());const body=new FormData();body.append("file",file);
    const response=await fetch(`/api/b9/admin/bulk/${kind}/preview`,{method:"POST",headers:{"x-flame-csrf":csrf.csrf},body});const data=await response.json();if(!response.ok)throw new B9Error(data,response.status);remember(data);
  });}
  const invalidRows=job?.rows.filter(row=>row.operation==="invalid")??[];
  const purposeErrors=invalidRows.some(row=>row.errors.some(error=>(error.includes("purposes.")&&error.includes("literal_error"))||error.includes("purposes:")));
  function showInvalidRow(){const first=invalidRows[0];if(!first||!job)return;setPage(Math.floor(job.rows.indexOf(first)/30));requestAnimationFrame(()=>document.getElementById(kind+"-bulk-row-"+first.row)?.scrollIntoView({block:"center"}));}
  function rowError(message:string){return message.includes("purposes.")&&message.includes("literal_error")?"purposes: use explain, demonstrate, practise, or human_help. This optional field may be left blank.":message;}
  async function commit(){if(!job)return;await act(async()=>{
    const saved=await b9Mutation<Job>("admin/bulk/imports/"+job.id+"/commit","POST",{preview_token:job.preview_token,confirm:confirmed});remember(saved);
    const result=saved.result;setNotice(`Import completed: ${result?.added??0} added, ${result?.merged??0} merged, ${result?.unchanged??0} unchanged. Existing values and publication states were preserved.`);
    try{await onImported();}catch{setError("Import completed, but the list could not refresh. Refresh the catalogue to see the confirmed changes.");}
  });}
  return <div className="bulk-transfer">
    <div className="bulk-transfer-actions"><button disabled={busy} onClick={()=>void show()}>Import Excel / ZIP</button><button disabled={busy} onClick={()=>void download("export")}>Export Excel</button>
      {(kind==="resources"||kind==="activity-kits")&&<button disabled={busy} onClick={()=>void download("export",true)}>Export with media</button>}
      <button disabled={busy} onClick={()=>void download("template")}>Download template</button><a href={`/bulk-import-samples/${kind}/${kind}.xlsx`} download>Sample Excel</a>{(kind==="resources"||kind==="activity-kits")&&<a href={`/bulk-import-samples/${kind}/${kind}.zip`} download>Sample ZIP</a>}<a href="/bulk-import-samples/README.md" target="_blank" rel="noreferrer">Package instructions</a></div>
    {notice&&<div role="status" className="b4-notice">{notice}<button aria-label="Dismiss bulk import message" onClick={()=>setNotice("")}>×</button></div>}
    {error&&!open&&<p role="alert">{error}</p>}
    <dialog ref={dialog} className="resource-library-dialog bulk-transfer-dialog" aria-labelledby={"bulk-title-"+kind} onCancel={e=>{e.preventDefault();void close();}}>
      <header><h3 id={"bulk-title-"+kind}>Bulk import {kind.replace("-"," ")}</h3><button disabled={busy} onClick={()=>void close()}>Close</button></header>
      <p>Record keys are optional: FLAME generates them when blank or omitted. For Excel mappings, supply matching keys in Records and Mappings; otherwise map after import. New templates omit existing IDs; exported IDs still identify exact existing items.</p>
      <p>Add new items and fill missing values on existing drafts. Nonempty values, existing media, publication status and saved mappings are preserved. New mappings are added, never removed.</p>
      {kind==="students"&&<p>New students are pending profiles. This does not create passwords, send invitations or grant membership. A verified sign-in is required to activate them.</p>}
      <div className="bulk-transfer-actions"><button disabled={busy} onClick={()=>void download("template")}>{kind==="students"?"Download student template":"Download template with current path IDs"}</button><a href={`/bulk-import-samples/${kind}/${kind}.xlsx`} download>Download sample Excel</a></div>
      {(!job||job.status!=="review"&&job.status!=="completed")&&<><label>Excel workbook or media package<input type="file" accept=".xlsx,.zip" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]??null);setError("");}}/></label><small>Up to 2,000 records; workbook 10 MiB; ZIP 120 MiB compressed / 200 MiB expanded. Put {kind}.xlsx at the ZIP root and media under assets/.</small><button disabled={busy||!file} onClick={()=>void preview()}>Validate and preview</button></>}
      {error&&open&&<p role="alert" className="b4-notice b4-notice-error">{error}</p>}{busy&&<p role="status">Processing bulk transfer…</p>}
      {job?.status==="review"&&<><h4>{job.filename}</h4><p>{job.total} rows · {job.counts.add} new · {job.counts.merge} merges · {job.counts.unchanged} unchanged · {job.counts.invalid} invalid</p>
        {job.counts.invalid>0&&<div className="b4-notice b4-notice-error" role="alert" id={"bulk-blocked-"+kind}><strong>Confirmation blocked: {job.counts.invalid} invalid rows.</strong><p>Correct the listed Excel cells, cancel this preview, and upload the corrected workbook or ZIP. No catalogue changes have been applied.</p>{purposeErrors&&<p>The purposes column accepts only explain, demonstrate, practise, or human_help. It is optional and may be blank.</p>}<button disabled={busy||!invalidRows.length} onClick={showInvalidRow}>Show first invalid row</button></div>}
        <div className="bulk-preview-scroll"><table><thead><tr><th>Excel row</th><th>Item / key</th><th>Operation</th><th>Review</th></tr></thead><tbody>{job.rows.slice(page*30,page*30+30).map(row=><tr id={kind+"-bulk-row-"+row.row} key={row.row}><td>{row.row}</td><td>{row.name}<small>{row.record_key}</small>{row.existing_id&&<small>Matched ID: {row.existing_id}</small>}</td><td>{row.operation}</td><td>{row.errors.map((e,i)=><p key={i}>{rowError(e)}</p>)}{row.fields_to_fill.length>0&&<p>Fill/add: {row.fields_to_fill.join(", ")}</p>}{row.preserved_fields.length>0&&<p>Keep existing: {row.preserved_fields.join(", ")}</p>}{row.mappings_to_add>0&&<p>{row.mappings_to_add} mappings to add</p>}</td></tr>)}</tbody></table></div>
        <nav className="bulk-transfer-actions" aria-label="Import preview pages"><button disabled={busy||page===0} onClick={()=>setPage(p=>p-1)}>Previous</button><span>{page*30+1}–{Math.min(job.total,page*30+30)} of {job.total}</span><button disabled={busy||(page+1)*30>=job.total} onClick={()=>setPage(p=>p+1)}>Next</button></nav>
        <label className="bulk-import-confirm"><input type="checkbox" aria-describedby={job.counts.invalid>0?"bulk-blocked-"+kind:undefined} disabled={busy||Boolean(job.counts.invalid)} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I confirm this additive import. Existing nonempty values will be preserved.</label>
        <div className="bulk-transfer-actions"><button disabled={busy||!confirmed||Boolean(job.counts.invalid)||!job.total} onClick={()=>void commit()}>Confirm import</button><button disabled={busy} onClick={()=>void act(async()=>{remember(await b9Mutation<Job>("admin/bulk/imports/"+job.id+"/review","POST",{}));setError("");})}>Review latest comparison</button><button disabled={busy} onClick={()=>void close()}>Cancel import</button></div>
        {job.counts.invalid>0&&<p>Nothing will be imported until the invalid rows are corrected. Cancel, correct the workbook, then upload again.</p>}
      </>}
      {job?.status==="completed"&&<><p role="status">Import completed. {job.result?.added} added; {job.result?.merged} merged; {job.result?.unchanged} unchanged; {job.result?.mappings_added} mappings added.</p><button onClick={()=>{remember(null);setFile(null);setOpen(false);}}>Return to catalogue</button></>}
    </dialog>
  </div>;
}
