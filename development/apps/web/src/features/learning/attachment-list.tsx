import { useEffect, useState } from "react";
import { FileText, X } from "lucide-react";
import { formatFileSize, type PromptAttachment } from "./prompt-attachments";
function AttachmentItem({ attachment, onRemove }: { attachment: PromptAttachment; onRemove?: (id: string) => void }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (attachment.kind === "file") return;
    const next = URL.createObjectURL(attachment.file); setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [attachment.file, attachment.kind]);
  return <li className={`attachment-item attachment-${attachment.kind}`}>
    {attachment.kind === "image" && url ? <a href={url} target="_blank" rel="noopener noreferrer" title={`Preview ${attachment.file.name}`}><img src={url} alt={attachment.file.name} /></a> : <FileText size={20} aria-hidden="true" />}
    <div className="attachment-copy"><span title={attachment.file.name}>{attachment.file.name}</span><small>{formatFileSize(attachment.file.size)} · {attachment.kind === "audio" ? "Audio" : attachment.kind === "image" ? "Image" : "File"}</small>{attachment.kind === "audio" && url && <audio controls preload="metadata" src={url} aria-label={`Play ${attachment.file.name}`} />}</div>
    {onRemove && <button type="button" className="icon-button" aria-label={`Remove ${attachment.file.name}`} title="Remove attachment" onClick={() => onRemove(attachment.id)}><X size={15} /></button>}
  </li>;
}
export function AttachmentList({ attachments, onRemove }: { attachments: PromptAttachment[]; onRemove?: (id: string) => void }) {
  if (!attachments.length) return null;
  return <ul className="attachment-list" aria-label={onRemove ? "Draft attachments" : "Question attachments"}>{attachments.map(attachment => <AttachmentItem key={attachment.id} attachment={attachment} onRemove={onRemove} />)}</ul>;
}
