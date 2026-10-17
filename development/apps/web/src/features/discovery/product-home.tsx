"use client";
import Link from "next/link";
import { FliplectureLogo } from "@/components/ui/fliplecture-logo";
import { useRouter } from "next/navigation";
import { BookOpen, Boxes, GraduationCap, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { FlamePromptInput } from "@/features/learning/flame-prompt-input";
import { ThemeToggle } from "@/features/learning/theme-toggle";
import { useLearningConversations } from "@/features/learning/use-learning-conversations";
import { emptySession } from "@/features/learning/conversation-types";
import { type ResponseLanguage } from "@/features/learning/response-languages";
import { catalogues, searchHref } from "./catalogue";
import { preferredResponseLanguage, saveQuestionIntent } from "./question-intent";

export function ProductHome({ signedIn }: { signedIn: boolean }) {
  const router = useRouter();
  const { sessions, setDraft, addFiles, removeAttachment } = useLearningConversations();
  const session = sessions.home ?? emptySession;
  const [language, setLanguage] = useState<ResponseLanguage>("en");
  useEffect(() => { setLanguage(preferredResponseLanguage()); }, []);
  function chooseLanguage(value: ResponseLanguage) {
    setLanguage(value);
    try { localStorage.setItem("flame:response-language", value); } catch { /* Current choice still applies. */ }
  }
  const [notice, setNotice] = useState("");
  const icons = [BookOpen, Boxes, Users, GraduationCap];
  function ask() {
    if (session.attachments.length) { setNotice("File processing and audio transcription aren't connected yet. Remove attachments to send your question as text."); return; }
    try { saveQuestionIntent(session.draft, language); setDraft("home", ""); router.push("/flame"); }
    catch { setNotice("Your browser couldn't keep this question for sign-in. Enable session storage and try again; your text is still here."); }
  }
  return <main className="discovery home-page">
    <header className="discovery-top"><Link href="/about">About Fliplecture</Link><div><ThemeToggle /><Link className="account-link" href={signedIn ? "/flame" : "/sign-in"}>{signedIn ? "My learning" : "Sign in"}</Link></div></header>
    <section className="home-centre" aria-labelledby="home-title">
      <h1 id="home-title" className="fliplecture-wordmark" aria-label="Fliplecture"><FliplectureLogo /></h1>
      <p className="home-tagline">A question can take you anywhere.</p>
      <div className="home-composer"><FlamePromptInput value={session.draft} pending={false} attachments={session.attachments}
        attachmentNotice={notice || session.attachmentNotice} onValueChange={value => { setDraft("home", value); setNotice(""); }}
        onFiles={files => addFiles("home", files)} onRemoveAttachment={id => removeAttachment("home", id)} onSubmit={ask}
        responseLanguage={language} onResponseLanguageChange={chooseLanguage} /></div>
      <nav className="home-catalogues" aria-label="Search Fliplecture catalogues">{catalogues.map((item, index) => { const Icon = icons[index]; return <Link key={item.id} href={searchHref(item.id, session.draft)}><Icon size={18} aria-hidden="true" />{item.label}</Link>; })}</nav>
      <p className="home-hint">Ask a question. Discover something useful. Keep learning.</p>
    </section>
    <footer className="discovery-footer"><span>Learning, with possibility.</span><Link href="/about">Meet FLAME, your learning assistant</Link></footer>
  </main>;
}
