"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { StudentAppShell } from "./student-app-shell";
import { ConversationViewport } from "./conversation-viewport";
import { FlameConversation } from "./flame-conversation";
import { FlamePromptInput } from "./flame-prompt-input";
import { QuestionAllowance } from "./question-allowance";
import { useLearningConversations } from "./use-learning-conversations";
import { emptySession, type ConversationTurn } from "./conversation-types";
import { isResponseLanguage, type ResponseLanguage } from "./response-languages";
import { takeQuestionIntent, saveQuestionIntent } from "@/features/discovery/question-intent";
import { catalogues, searchHref } from "@/features/discovery/catalogue";
const key = "guest-curiosity";
export function GuestWorkspace() {
  const router = useRouter(), {sessions,setDraft,addFiles,removeAttachment,submit} = useLearningConversations();
  const session = sessions[key] ?? emptySession;
  const pending = session.turns.some(turn=>turn.status === "pending");
  const [notice,setNotice] = useState("");
  const [language,setLanguage] = useState<ResponseLanguage>("en"),read = useRef(false);
  useEffect(()=>{
    if(read.current)return;read.current=true;
    try {const saved=localStorage.getItem("flame:response-language");if(isResponseLanguage(saved))setLanguage(saved);}catch{}
    const intent=takeQuestionIntent(true);if(!intent)return;
    setLanguage(intent.language);setDraft(key,intent.question);
    void submit(key,{guest:true,message:intent.question,mode:"curiosity",context:null,responseLanguage:intent.language,catalogueItem:intent.item},undefined,intent.id);
  },[]);
  function send(retry?: ConversationTurn) {
    if(pending)return;
    void submit(key,{guest:true,message:retry?.question ?? session.draft,attachments:retry?.attachments ?? session.attachments,mode:"curiosity",context:null,responseLanguage:language},retry?.id);
  }
  function rememberQuestion() {
    try { if(session.draft.trim())saveQuestionIntent(session.draft,language,undefined,true);return true; }
    catch {setNotice("Your browser could not keep this question for sign-in. Copy your question or enable session storage before continuing.");return false;}
  }
  const navigation=<div className="guest-navigation"><h2>Explore with FLAME</h2><p>Ask questions in Curiosity. Sign in to use Study and save learning to your student account.</p><nav aria-label="Search Fliplecture catalogues">{catalogues.map(item=><Link key={item.id} href={searchHref(item.id)}>{item.label}</Link>)}</nav><Link className="account-link" href="/sign-in?next=%2Fflame" onClick={event=>{if(!rememberQuestion())event.preventDefault();}}>Sign in</Link></div>;
  return <StudentAppShell guest accountAllowance={<QuestionAllowance guest onSignIn={rememberQuestion} />} mode="curiosity" onModeChange={mode=>{if(mode==="study")router.push("/sign-in?next=%2Fflame%3Fmode%3Dstudy");}} navigation={navigation} breadcrumb={<span>Curiosity</span>}>
    <ConversationViewport sessionId={`${router.bfcacheId}:${key}`}>
      <h1>Follow your curiosity</h1>
      {session.turns.length ? <FlameConversation turns={session.turns} pending={pending} onRetry={send} /> : <div className="welcome"><p>Ask FLAME a question to get started. You can explore 10 questions each day without signing in.</p></div>}
    </ConversationViewport>
    <FlamePromptInput value={session.draft} attachments={session.attachments} attachmentNotice={notice || session.attachmentNotice} pending={pending} onValueChange={value=>{setNotice("");setDraft(key,value);}} onFiles={files=>addFiles(key,files)} onRemoveAttachment={id=>removeAttachment(key,id)} onSubmit={()=>send()} responseLanguage={language} onResponseLanguageChange={value=>{setLanguage(value);try{localStorage.setItem("flame:response-language",value);}catch{}}} />
  </StudentAppShell>;
}
