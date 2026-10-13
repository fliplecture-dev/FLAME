"use client";
import { useEffect, useId, useRef, useState } from "react";
import { MediaPreview } from "./resource-library-ui";

export function HtmlSourceEditor({document,loading,error,disabled,title,onChange,onRetry,onReading}:{document:string;loading:boolean;error:string;disabled:boolean;title:string;onChange:(file:File)=>void;onRetry:()=>void;onReading:(reading:boolean)=>void}) {
  const [code,setCode]=useState(document), [preview,setPreview]=useState(""), [tab,setTab]=useState("code"), [reading,setReading]=useState(false), [fileError,setFileError]=useState("");
  const edited=useRef(false), sequence=useRef(0), filename=useRef("interactive.html"), codeTab=useRef<HTMLButtonElement>(null), previewTab=useRef<HTMLButtonElement>(null);
  const id=useId();
  useEffect(()=>{if(!edited.current)setCode(document);},[document]);
  useEffect(()=>()=>{sequence.current++;onReading(false);},[]);
  const size=new Blob([code]).size, valid=Boolean(code.trim())&&size<=2*1024*1024;
  function selectTab(value:string){if(value==="preview")setPreview(code);setTab(value);}
  function navigate(event:React.KeyboardEvent){if(["ArrowLeft","ArrowRight","Home","End"].includes(event.key)){event.preventDefault();const next=event.key==="Home"?"code":event.key==="End"?"preview":tab==="code"?"preview":"code";if(next==="preview"&&!valid)return;selectTab(next);(next==="code"?codeTab:previewTab).current?.focus();}}
  async function load(file:File){
    const request=++sequence.current;setFileError("");
    if(!/\.html?$/i.test(file.name)||file.type&&file.type!=="text/html"){setFileError("Choose one .html or .htm file. Existing code has been preserved.");return;}
    if(file.size>2*1024*1024){setFileError("HTML exceeds the 2 MiB limit. Existing code has been preserved.");return;}
    setReading(true);onReading(true);
    try{
      const value=new TextDecoder("utf-8",{fatal:true}).decode(await file.arrayBuffer());if(request!==sequence.current)return;
      if(!value.trim())throw new Error("The HTML file is empty.");
      edited.current=true;filename.current=file.name;setCode(value);setTab("code");setPreview("");onChange(new File([value],file.name,{type:"text/html"}));
    }catch(cause){if(request===sequence.current)setFileError((cause instanceof Error?cause.message:"File could not be read.")+" Use a UTF-8 HTML file. Existing code has been preserved.");}
    finally{if(request===sequence.current){setReading(false);onReading(false);}}
  }
  return <section className="resource-html-editor" aria-label="HTML5 source editor">
    <div className="resource-html-toolbar"><div role="tablist" aria-label="Interactive editor views" onKeyDown={navigate}>
      <button ref={codeTab} id={id+"-code-tab"} role="tab" aria-selected={tab==="code"} aria-controls={id+"-code"} tabIndex={tab==="code"?0:-1} onClick={()=>selectTab("code")}>Code (edit / paste)</button>
      <button ref={previewTab} id={id+"-preview-tab"} role="tab" aria-selected={tab==="preview"} aria-controls={id+"-preview"} tabIndex={tab==="preview"?0:-1} disabled={!valid||reading||loading&&!edited.current} onClick={()=>selectTab("preview")}>Preview</button>
    </div><label>Upload HTML5 file<input type="file" aria-label="Upload HTML5 file" accept=".html,.htm,text/html" disabled={disabled||reading} onChange={event=>{const file=event.target.files?.[0];event.target.value="";if(file)void load(file);}}/></label></div>
    <p>Upload a single HTML file to populate Code, or paste/edit it here. Open Preview to try the current code.</p>
    <div id={id+"-code"} role="tabpanel" aria-labelledby={id+"-code-tab"} hidden={tab!=="code"}><label>HTML5 code<textarea aria-label="HTML5 code" value={code} disabled={disabled||reading||loading&&!edited.current} spellCheck={false} autoCapitalize="off" autoCorrect="off" wrap="off" placeholder="Paste your complete HTML document here…" onChange={event=>{const value=event.target.value;edited.current=true;setCode(value);setFileError("");onChange(new File([value],filename.current,{type:"text/html"}));}}/></label></div>
    <div id={id+"-preview"} role="tabpanel" aria-labelledby={id+"-preview-tab"} hidden={tab!=="preview"}>{tab==="preview"&&preview&&<MediaPreview url="" type="interactive" htmlDocument={preview} description={title||"Interactive HTML preview"}/>}</div>
    <small>{(size/1024).toFixed(1)} KiB / 2048 KiB. Include CSS, JavaScript and assets in this single file. Save draft stores the HTML; publication remains a separate action.</small>
    {loading&&<p role="status">Loading saved HTML…</p>}{reading&&<p role="status">Reading HTML file…</p>}{fileError&&<p role="alert">{fileError}</p>}
    {error&&<p role="alert">{error} <button disabled={disabled} onClick={onRetry}>Retry loading HTML</button></p>}
    {size>2*1024*1024&&<p role="alert">HTML exceeds the 2 MiB limit. Reduce the code or embedded assets before saving.</p>}
  </section>;
}
