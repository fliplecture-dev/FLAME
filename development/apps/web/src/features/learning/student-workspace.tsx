"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { b4Mutation, forgetLearningAnswerSession } from "@/lib/api/student-learning";
import { learningFromMemberships, type Membership } from "@/lib/api/b4-catalogue";
import { BookOpen, ChevronRight, Home, Lightbulb, Pin } from "lucide-react";
import { LearningLibrary } from "@/features/curriculum/learning-library";
import { RemovalConfirmation } from "@/components/ui/removal-confirmation";
import { mergeLearningPath } from "@/features/curriculum/merge-learning-path";
import { firstBranchKeys, contextKey, ancestorKeys, requestContext } from "@/features/curriculum/learning-tree";
import { CurriculumNavigator, type TreeViewState } from "@/features/curriculum/curriculum-navigator";
import type { Curriculum, Subject, TopicContext } from "@/features/curriculum/types";
import { FlamePromptInput } from "./flame-prompt-input";
import { isResponseLanguage, type ResponseLanguage } from "./response-languages";
import { LearningContent } from "./learning-content";
import { StudentAppShell } from "./student-app-shell";
import { ExploreWorkspace } from "./explore-workspace";
import type { LearningMode } from "./mode-switcher";
import { LearningShortcuts, type LearningShortcut } from "./learning-shortcuts";
import { clearRecentHistory, deleteSavedSession, getSavedMessages, getAllSavedSessions, markConversationOpened, pinSavedSession, unpinAllConversations, type SavedSession } from "./saved-sessions";
import { groupRecentSessions, recentTitle } from "./recent-sessions";
import { findSavedContext, restoredTurns } from "./restore-saved-session";

import { useLearningConversations } from "./use-learning-conversations";
import { emptySession, type ConversationTurn } from "./conversation-types";
import { FlameConversation } from "./flame-conversation";
import { ConversationViewport } from "./conversation-viewport";
import { ResourceRecommendations } from "./resource-recommendations";
import { gravityDevelopmentResources } from "./development-resources";
import { gravityDevelopmentContent } from "./development-content";
function SubtopicActions({ context, onSelect }: { context: TopicContext; onSelect: (value: TopicContext) => void }) {
  return <section className="subtopic-actions" aria-label={`Subtopics in ${context.topic.name}`}>
    <h2>Subtopics</h2>
    <div className="subtopic-action-list">
      {context.topic.subtopics.map(subtopic => <button key={subtopic.id} className="subtopic-action" onClick={() => onSelect({ ...context, subtopic })}>{subtopic.name}</button>)}
    </div>
  </section>;
}

function TopicFamilyNavigation({ context, onSelect }: { context: TopicContext; onSelect: (value: TopicContext) => void }) {
  return <nav className="topic-family-nav" aria-label={`Explore ${context.topic.name}`}>
    <button className="topic-family-topic" aria-label={`View ${context.topic.name} topic`} onClick={() => onSelect({ ...context, subtopic: undefined })}>
      <BookOpen size={18} aria-hidden="true" /><span><small>Topic</small><strong>{context.topic.name}</strong></span>
    </button>
    <div className="topic-family-subtopics"><span className="topic-family-label">Subtopics</span>
      <div className="topic-family-list">{context.topic.subtopics.map(subtopic => <button key={subtopic.id}
        className={`topic-family-subtopic ${context.subtopic?.id === subtopic.id ? "selected" : ""}`}
        aria-current={context.subtopic?.id === subtopic.id ? "page" : undefined}
        onClick={() => onSelect({ ...context, subtopic })}>{subtopic.name}</button>)}</div>
    </div>
  </nav>;
}

export function StudentWorkspace({ curricula, catalogue = [], memberships = [], live = false }: { curricula: Curriculum[]; catalogue?: Curriculum[]; memberships?: Membership[]; live?: boolean }) {
  const [responseLanguage, setResponseLanguage] = useState<ResponseLanguage>("en");
  useEffect(() => {
    try { const saved = localStorage.getItem("flame:response-language"); if (isResponseLanguage(saved)) setResponseLanguage(saved); } catch { /* Browser storage is optional. */ }
  }, []);
  function chooseResponseLanguage(value: ResponseLanguage) {
    setResponseLanguage(value);
    try { localStorage.setItem("flame:response-language", value); } catch { /* Current-tab selection still works. */ }
  }
  const [learning, setLearning] = useState(curricula);
  const curiositySuggestions = [
    "Why is the sky blue?", "How do computers work?", "What are fractions?",
    "Why do countries have governments?", "How do I say hello in Spanish?",
  ];
  const visitKey = useRef<string | null>(null);
  useEffect(() => {
    if (!live) return;
    visitKey.current ??= crypto.randomUUID();
    void b4Mutation("me/activity", "POST", { event_type: "visit", deduplication_key: visitKey.current }).catch(() => {});
  }, [live]);
  const [savedMemberships, setSavedMemberships] = useState(memberships);
  const removedCurricula = useRef(new Map<string, Curriculum>());
  const removedSubjects = useRef(new Map<string, Subject>());
  const [removal, setRemoval] = useState<{ curriculum: Curriculum; levelId?: string; subject?: Subject; after?: () => void } | null>(null);
  const [removalNotice, setRemovalNotice] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false);
  async function addLearning(path: Curriculum[], kind = "Curriculum") {
    if (live) {
      const c = path[0], l = c?.levels[0], subject = l?.subjects[0], domain = subject?.domains[0], topic = domain?.topics[0], subtopic = topic?.subtopics[0];
      if (!c) return;
      const row = await b4Mutation("me/learning", "POST", {
        curriculum_id: c.id,
        level_id: kind === "Curriculum" ? null : l?.id ?? null,
        subject_id: kind === "Curriculum" ? null : subject?.id ?? null,
        domain_id: kind === "Topic" || kind === "Subtopic" ? domain?.id ?? null : null,
        category_id: kind === "Topic" || kind === "Subtopic" ? topic?.categoryId ?? null : null,
        topic_id: kind === "Topic" || kind === "Subtopic" ? topic?.id ?? null : null,
        subtopic_id: kind === "Subtopic" ? subtopic?.id ?? null : null,
      }) as Membership;
      let next = [...savedMemberships.filter(m => m.id !== row.id), row];
      if (kind === "Curriculum" || (subject && l)) {
        for (const hidden of next.filter(m => m.curriculum_id === c.id && !m.visible &&
          (kind === "Curriculum" || (m.subject_id === subject?.id && m.level_id === l?.id && !m.domain_id)))) {
          const restored = await b4Mutation("me/learning/" + hidden.id, "PATCH", {
            visible: true, expected_version: hidden.version,
          }) as Membership;
          next = next.map(m => m.id === restored.id ? restored : m);
        }
      }
      setSavedMemberships(next);
      setLearning(learningFromMemberships(catalogue, next));
      setRemovalNotice("");
      setMode("study");
      setView(prev => ({ query: "", filter: "all", expanded: Array.from(new Set([...prev.expanded, ...firstBranchKeys(path)])) }));
      return;
    }
    const savedCurricula = path.flatMap(c => {
      const saved = removedCurricula.current.get(c.id);
      return saved && !learning.some(current => current.id === c.id) ? [saved] : [];
    });
    const savedSubjects = path.map(c => ({ ...c, levels: c.levels.map(l => ({ ...l, subjects: l.subjects.flatMap(s => {
      const saved = removedSubjects.current.get(JSON.stringify([c.id, l.id, s.id]));
      return saved ? [saved] : [];
    }) })).filter(l => l.subjects.length) })).filter(c => c.levels.length);
    setLearning(prev => mergeLearningPath(mergeLearningPath(mergeLearningPath(prev, savedCurricula), savedSubjects), path));
    path.forEach(c => {
      removedCurricula.current.delete(c.id);
      c.levels.forEach(l => l.subjects.forEach(s => removedSubjects.current.delete(JSON.stringify([c.id, l.id, s.id]))));
    });
    setRemovalNotice("");
    setMode("study");
    setView(prev => ({ query: "", filter: "all", expanded: Array.from(new Set([...prev.expanded, ...firstBranchKeys(path)])) }));
  }
  const [view, setView] = useState<TreeViewState>(() => {
    return { query: "", filter: "all", expanded: firstBranchKeys(curricula) };
  });
  const [mode, setMode] = useState<LearningMode>("study");
  const [selected, setSelected] = useState<TopicContext | null>(null);
  const [resumed, setResumed] = useState<SavedSession | null>(null);
  const { sessions, setDraft, restore, forget, addFiles, removeAttachment, submit } = useLearningConversations(live);
  const [recent, setRecent] = useState<LearningShortcut[]>([]);
  const [savedRows, setSavedRows] = useState<SavedSession[]>([]);
  const [sectionOpen, setSectionOpen] = useState({ Pinned: true, Recent: true, MyLearning: true });
  const [pinBusy, setPinBusy] = useState(false);
  const [openedConversationId, setOpenedConversationId] = useState<string | null>(null);
  const sidebarGeneration = useRef(0);
  useEffect(() => {
    try {
      const value = JSON.parse(localStorage.getItem("flame:conversation-sections") ?? "{}");
      setSectionOpen({ Pinned: value.Pinned !== false, Recent: value.Recent !== false, MyLearning: value.MyLearning !== false });
    } catch { /* Default to expanded if preferences are unavailable. */ }
  }, []);
  function changeSection(title: "Pinned" | "Recent" | "MyLearning", expanded: boolean) {
    setSectionOpen(previous => {
      const next = { ...previous, [title]: expanded };
      try { localStorage.setItem("flame:conversation-sections", JSON.stringify(next)); } catch { /* Storage may be disabled. */ }
      return next;
    });
  }
  const [recentNotice, setRecentNotice] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const resumeRequest = useRef(0);
  useEffect(() => {
    if (!live) return;
    const refresh = () => {
      const generation = ++sidebarGeneration.current;
      void getAllSavedSessions().then(rows => {
        if (generation === sidebarGeneration.current) setSavedRows(rows);
      }).catch(error => setRecentNotice(error instanceof Error ? error.message : "Conversations could not be loaded."));
    };
    refresh();
    window.addEventListener("flame:sessions-updated", refresh);
    return () => window.removeEventListener("flame:sessions-updated", refresh);
  }, [live]);
  const heading = useRef<HTMLHeadingElement>(null);
  const activeId = resumed?.mode === mode ? resumed.id : mode === "curiosity" ? "curiosity" : selected ? contextKey(selected) : "study";
  const session = sessions[activeId] ?? emptySession;
  const context = mode === "study" ? selected : null;
  const pending = session.turns.some(turn => turn.status === "pending");
  function sendQuestion(retry?: ConversationTurn) {
    const message = retry?.question ?? session.draft.trim();
    const attachments = retry?.attachments ?? session.attachments;
    if ((!message && !attachments.length) || pending || loadingHistory || (live && mode === "study" && resumed && !context)) return;
    const history = session.turns.filter(turn => turn.status === "complete").map(turn => ({ question: turn.question, blocks: turn.blocks, attachments: turn.attachments }));
    void submit(activeId, mode === "study" ? { message, attachments, mode, context: context ? requestContext(context) : null, history, sessionId: resumed?.id, responseLanguage } : { message, attachments, mode, context: null, history, sessionId: resumed?.id, responseLanguage }, retry?.id);
    if (!live && mode === "curiosity") remember({ id: "curiosity", title: session.turns[0]?.question ?? message, mode });
  }
  function removeCurriculum(id: string) {
    const curriculum = learning.find(c => c.id === id);
    if (!curriculum) return;
    removedCurricula.current.set(id, curriculum);
    setLearning(prev => prev.filter(c => c.id !== id));
    setRecent(prev => prev.filter(item => item.context?.curriculum.id !== id));
    if (selected?.curriculum.id === id) setSelected(null);
    setRemovalNotice(curriculum.name + " removed. Add it again from Library to restore progress in this tab.");
  }
  function requestRemoval(id: string, levelId?: string, subjectId?: string, after?: () => void) {
    const curriculum = learning.find(c => c.id === id);
    const subject = subjectId ? curriculum?.levels.find(l => l.id === levelId)?.subjects.find(s => s.id === subjectId) : undefined;
    if (!curriculum || (subjectId && !subject)) return;
    setRemoval({ curriculum, levelId, subject, after });
  }
  async function confirmRemoval() {
    if (!removal) return;
    const { curriculum, levelId, subject, after } = removal;
    if (live) {
      try {
        let next = [...savedMemberships];
        if (subject && levelId) {
          let target = next.find(m => m.curriculum_id === curriculum.id && m.level_id === levelId && m.subject_id === subject.id && !m.domain_id);
          if (!target) {
            target = await b4Mutation("me/learning", "POST", {
              curriculum_id: curriculum.id, level_id: levelId, subject_id: subject.id,
            }) as Membership;
            next.push(target);
          }
          if (target.visible) {
            const hidden = await b4Mutation("me/learning/" + target.id, "PATCH", {
              visible: false, expected_version: target.version,
            }) as Membership;
            next = next.map(m => m.id === hidden.id ? hidden : m);
          }
        } else {
          for (const target of next.filter(m => m.curriculum_id === curriculum.id && m.visible)) {
            const hidden = await b4Mutation("me/learning/" + target.id, "PATCH", {
              visible: false, expected_version: target.version,
            }) as Membership;
            next = next.map(m => m.id === hidden.id ? hidden : m);
          }
        }
        setSavedMemberships(next);
        setLearning(learningFromMemberships(catalogue, next));
        if (selected?.curriculum.id === curriculum.id && (!subject || selected.subject.id === subject.id)) setSelected(null);
        setRecent(prev => prev.filter(item => item.context?.curriculum.id !== curriculum.id || (subject && item.context.subject.id !== subject.id)));
        setRemovalNotice((subject?.name ?? curriculum.name) + " hidden. Add it from Library to restore it.");
        setRemoval(null);
        after?.();
      } catch (error) {
        setRemovalNotice(error instanceof Error ? error.message : "The change could not be saved.");
      }
      return;
    }
    if (!subject || !levelId) removeCurriculum(curriculum.id);
    else {
      removedSubjects.current.set(JSON.stringify([curriculum.id, levelId, subject.id]), subject);
      setLearning(prev => prev.map(c => c.id === curriculum.id ? { ...c, levels: c.levels.map(l => l.id === levelId ? { ...l, subjects: l.subjects.filter(s => s.id !== subject.id) } : l) } : c));
      const keepShortcut = (item: LearningShortcut) => item.context?.curriculum.id !== curriculum.id || item.context.level.id !== levelId || item.context.subject.id !== subject.id;
      setRecent(prev => prev.filter(keepShortcut));
      if (selected?.curriculum.id === curriculum.id && selected.level.id === levelId && selected.subject.id === subject.id) setSelected(null);
      setRemovalNotice(subject.name + " removed. Add it again from Library to restore progress in this tab.");
    }
    setRemoval(null);
    after?.();
  }
  function remember(item: LearningShortcut) {
    setRecent(previous => [{ ...item, recentAt: new Date().toISOString(), pinned: previous.find(row => row.id === item.id)?.pinned ?? item.pinned }, ...previous.filter(row => row.id !== item.id)]);
  }
  function shortcut(row: SavedSession): LearningShortcut {
    return { id: row.id, title: recentTitle(row), mode: row.mode, pinned: row.pinned, recentAt: row.recent_at,
      context: row.mode === "study" ? findSavedContext(catalogue, row) ?? undefined : undefined };
  }
  const conversationItems = live ? savedRows.filter(row => row.first_question?.trim() || row.pinned).map(shortcut) : recent;
  const pinnedItems = conversationItems.filter(item => item.pinned);
  const recentItems = live ? groupRecentSessions(savedRows.filter(row => !row.pinned && row.recent_at && row.first_question?.trim())
    .sort((a, b) => (b.recent_at ?? "").localeCompare(a.recent_at ?? ""))).map(group => shortcut(group[0])).sort((a, b) => (b.recentAt ?? "").localeCompare(a.recentAt ?? "")) : recent.filter(item => !item.pinned && item.recentAt);
  const activeConversationId = live ? session.turns.filter(turn => turn.sessionId).at(-1)?.sessionId ?? openedConversationId ?? resumed?.id : activeId;
  const currentShortcut: LearningShortcut | null = activeConversationId && (resumed || session.turns.length || (!live && context)) ? {
    id: activeConversationId,
    title: context?.subtopic?.name ?? context?.topic.name ?? session.turns[0]?.question ?? (resumed ? recentTitle(resumed) : "Conversation"),
    mode, context: context ?? undefined,
    pinned: live ? Boolean(savedRows.find(row => row.id === activeConversationId)?.pinned) : Boolean(recent.find(row => row.id === activeConversationId)?.pinned),
  } : null;
  async function openSaved(item: LearningShortcut) {
    const row = savedRows.find(row => row.id === item.id);
    if (!row) return;
    const request = ++resumeRequest.current;
    setLoadingHistory(true); setRecentNotice("");
    try {
      const messages = await getSavedMessages(row.id);
      if (request !== resumeRequest.current) return;
      const path = row.mode === "study" ? findSavedContext(catalogue, row) : null;
      const currentRevision = row.mode === "curiosity" || !path || row.revision === path.curriculum.revision;
      const key = currentRevision || !path ? row.id : contextKey(path);
      if (!currentRevision) forgetLearningAnswerSession(row.id);
      restore(key, restoredTurns(messages, row.id));
      setOpenedConversationId(row.id);
      setSelected(path); setMode(row.mode); setResumed(currentRevision || !path ? row : null);
      const stamp = new Date().toISOString();
      sidebarGeneration.current += 1;
      setSavedRows(previous => previous.map(item => item.id === row.id ? { ...item, recent_at: stamp } : item));
      void markConversationOpened(row.id).catch(error => setRecentNotice(error instanceof Error ? error.message : "Recent history could not be updated."));
      if (path) setView(prev => ({ ...prev, query: "", filter: "all", expanded: Array.from(new Set([...prev.expanded, ...ancestorKeys(path)])) }));
      requestAnimationFrame(() => heading.current?.focus({ preventScroll: true }));
    } catch (error) {
      if (request === resumeRequest.current) setRecentNotice(error instanceof Error ? error.message : "Conversation could not be opened.");
    } finally { if (request === resumeRequest.current) setLoadingHistory(false); }
  }
  function selectTopic(value: TopicContext) {
    resumeRequest.current += 1;
    setLoadingHistory(false); setOpenedConversationId(null); setResumed(null); setMode("study"); setSelected(value);
    setView(prev => ({ ...prev, expanded: Array.from(new Set([...prev.expanded, ...ancestorKeys(value)])) }));
    if (live) {
      const match = conversationItems.find(item => item.mode === "study" && item.context && contextKey(item.context) === contextKey(value));
      if (match) void openSaved(match);
    } else remember({ id: contextKey(value), title: value.subtopic?.name ?? value.topic.name, mode: "study", context: value });
    requestAnimationFrame(() => heading.current?.focus({ preventScroll: true }));
  }
  function openShortcut(item: LearningShortcut) {
    if (live) { void openSaved(item); return; }
    setResumed(null);
    if (item.context) { setView(prev => ({ ...prev, query: "", filter: "all" })); selectTopic(item.context); }
    else { setMode("curiosity"); remember(item); }
  }
  async function toggleRecentPin(item: LearningShortcut) {
    if (pinBusy) return;
    if (!live) { setRecent(previous => previous.map(row => row.id === item.id ? { ...row, pinned: !row.pinned, recentAt: row.recentAt ?? new Date().toISOString() } : row)); return; }
    const previous = savedRows.find(row => row.id === item.id);
    const target = !item.pinned;
    sidebarGeneration.current += 1;
    setPinBusy(true); setRecentNotice("");
    const stamp = new Date().toISOString();
    const path = item.context;
    const optimistic: SavedSession = previous ?? {
      id: item.id, mode: item.mode, pinned: false, revision: path?.curriculum.revision ?? null,
      created_at: stamp, updated_at: stamp, recent_at: stamp,
      first_question: session.turns[0]?.question || item.title,
      context: path ? { curriculum_id: path.curriculum.id, level_id: path.level.id, subject_id: path.subject.id,
        domain_id: path.domain.id, category_id: path.topic.categoryId, topic_id: path.topic.id,
        subtopic_id: path.subtopic?.id ?? null, names: { topic: path.topic.name, subtopic: path.subtopic?.name ?? null } } : null,
    };
    setSavedRows(rows => rows.some(row => row.id === item.id)
      ? rows.map(row => row.id === item.id ? { ...row, pinned: target, recent_at: row.recent_at ?? stamp } : row)
      : [{ ...optimistic, pinned: target }, ...rows]);
    try {
      const changed = await pinSavedSession(item.id, target);
      setSavedRows(rows => rows.some(row => row.id === item.id) ? rows.map(row => row.id === item.id ? { ...row, ...changed, first_question: row.first_question || session.turns[0]?.question || item.title } : row)
        : [{ ...changed, first_question: session.turns[0]?.question || item.title }, ...rows]);
    } catch (error) {
      setSavedRows(rows => previous ? rows.map(row => row.id === previous.id ? previous : row) : rows.filter(row => row.id !== item.id));
      setRecentNotice(error instanceof Error ? error.message : "Pin could not be changed.");
    } finally { setPinBusy(false); }
  }
  async function clearRecent() {
    if (!window.confirm("Clear recent history? Conversations and pinned items will be kept.")) return;
    if (!live) { setRecent(rows => rows.map(row => row.pinned ? row : { ...row, recentAt: null })); return; }
    if (pinBusy) return;
    sidebarGeneration.current += 1; setPinBusy(true);
    try {
      await clearRecentHistory();
      setSavedRows(rows => rows.map(row => row.pinned ? row : { ...row, recent_at: null }));
      setRecentNotice("Recent history cleared. Conversations are kept.");
    } catch (error) { setRecentNotice(error instanceof Error ? error.message : "Recent history could not be cleared."); }
    finally { setPinBusy(false); }
  }
  async function unpinAll() {
    if (!window.confirm("Unpin all conversations? Your conversations will be kept.")) return;
    const stamp = new Date().toISOString();
    if (!live) { setRecent(rows => rows.map(row => row.pinned ? { ...row, pinned: false, recentAt: stamp } : row)); return; }
    if (pinBusy) return;
    sidebarGeneration.current += 1; setPinBusy(true);
    try {
      await unpinAllConversations();
      setSavedRows(rows => rows.map(row => row.pinned ? { ...row, pinned: false, recent_at: stamp } : row));
      setRecentNotice("All conversations unpinned.");
    } catch (error) { setRecentNotice(error instanceof Error ? error.message : "Conversations could not be unpinned."); }
    finally { setPinBusy(false); }
  }
  async function deleteRecent(item: LearningShortcut) {
    if (!window.confirm(`Delete ${item.title} and its conversation history?`)) return;
    if (!live) { setRecent(rows => rows.filter(row => row.id !== item.id)); forget(item.id); return; }
    try {
      await deleteSavedSession(item.id); forgetLearningAnswerSession(item.id); forget(item.id);
      sidebarGeneration.current += 1;
      setSavedRows(rows => rows.filter(row => row.id !== item.id));
      if (activeConversationId === item.id) { setOpenedConversationId(null); setResumed(null); setSelected(null); setMode("study"); }
      setRecentNotice("Conversation deleted.");
    } catch (error) { setRecentNotice(error instanceof Error ? error.message : "Conversation could not be deleted."); }
  }
  const conversationPin = currentShortcut && <button className={`icon-button conversation-pin ${currentShortcut.pinned ? "is-pinned" : ""}`} disabled={pinBusy || loadingHistory} aria-pressed={Boolean(currentShortcut.pinned)} title={currentShortcut.pinned ? "Unpin conversation" : "Pin conversation"} aria-label={currentShortcut.pinned ? "Unpin conversation" : "Pin conversation"} onClick={() => void toggleRecentPin(currentShortcut)}><Pin size={17} fill={currentShortcut.pinned ? "currentColor" : "none"} aria-hidden="true" /></button>;
  // Keep the large curriculum tree stable while the prompt draft changes on each keystroke.
  const curriculumNavigation = useMemo(() => <CurriculumNavigator
    sectionExpanded={sectionOpen.MyLearning}
    onSectionExpandedChange={expanded => changeSection("MyLearning", expanded)}
    live={live}
    onRemoveCurriculum={id => requestRemoval(id)}
    onRemoveSubject={(id, levelId, subjectId) => requestRemoval(id, levelId, subjectId)}
    curricula={learning}
    onOpenLibrary={() => setLibraryOpen(true)}
    view={view}
    onViewChange={setView}
    selectedId={selected ? contextKey(selected) : undefined}
    onSelect={selectTopic}
  />, [live, learning, view, selected, savedRows, sectionOpen.MyLearning]);
  const navigation = <>
    <LearningShortcuts title="Pinned" items={pinnedItems} activeId={activeConversationId ?? activeId} expanded={sectionOpen.Pinned} onExpandedChange={expanded => changeSection("Pinned", expanded)} onSelect={openShortcut} onPin={item => void toggleRecentPin(item)} onDelete={item => void deleteRecent(item)} onSectionAction={() => void unpinAll()} busy={pinBusy} />
    <LearningShortcuts title="Recent" items={recentItems} activeId={activeConversationId ?? activeId} expanded={sectionOpen.Recent} onExpandedChange={expanded => changeSection("Recent", expanded)} onSelect={openShortcut} onPin={item => void toggleRecentPin(item)} onDelete={item => void deleteRecent(item)} onSectionAction={() => void clearRecent()} busy={pinBusy} />
    {recentNotice && <p className="recent-notice" role="status">{recentNotice}</p>}
    {mode === "study" ? curriculumNavigation : <div className="curiosity-sidebar-note"><Lightbulb size={18} aria-hidden="true" /><p>Follow your curiosity.<span>Your explorations don’t change academic progress.</span></p></div>}
  </>;
  const breadcrumb = <nav aria-label="Learning context"><Home size={17} aria-hidden="true" />{context ? [context.curriculum.name, context.level.name, context.subject.name, context.domain.name, context.topic.name, ...(context.subtopic ? [context.subtopic.name] : [])].map((name, i) => <span key={i} className={i === 5 ? "current-crumb" : i === 0 || i === 1 || i === 3 ? "detail-crumb" : ""}><ChevronRight size={14} aria-hidden="true" />{name}</span>) : <span>{mode === "curiosity" ? "Curiosity" : "My learning space"}</span>}</nav>;
  return <ExploreWorkspace catalogue={catalogue} context={context} curiosity={mode === "curiosity"} curiosityTurn={mode === "curiosity" ? session.turns.at(-1) ?? null : null} live={live}>{(exploreTrigger, explorePanel) => <StudentAppShell headerAction={exploreTrigger} explorePanel={explorePanel} mode={mode} onModeChange={next => { resumeRequest.current += 1; setLoadingHistory(false); setOpenedConversationId(null); setResumed(null); setMode(next); }} breadcrumb={breadcrumb} navigation={navigation}>
    <ConversationViewport sessionId={activeId}>
      {removalNotice && <p className="removal-notice" role="status">{removalNotice}</p>}
      {loadingHistory && <p className="removal-notice" role="status">Loading conversation…</p>}
      {live && mode === "study" && resumed && !context && <p className="removal-notice" role="status">This topic is no longer published. Its conversation history is available to read.</p>}
      <div className="context-actions"><span className="concept-label">{mode === "study" ? <BookOpen size={16} aria-hidden="true" /> : <Lightbulb size={16} aria-hidden="true" />}{mode === "curiosity" ? "Curiosity" : context?.subtopic ? "Subtopic" : context ? "Topic" : "Your learning space"}</span></div>
      {context ? <section className="topic-workspace">
        {context.subtopic && <TopicFamilyNavigation context={context} onSelect={selectTopic} />}
        <div className="conversation-title-row"><h1 ref={heading} tabIndex={-1}>{context.subtopic?.name ?? context.topic.name}</h1>{conversationPin}</div>
        {!context.subtopic && <SubtopicActions context={context} onSelect={selectTopic} />}
        {context.subtopic?.description && <p className="topic-description">{context.subtopic.description}</p>}
        {!session.turns.length && <p className="learning-empty">Ask FLAME a question about {(context.subtopic?.name ?? context.topic.name).toLowerCase()} to start exploring.</p>}
      </section> : !session.turns.length ? <section className="welcome"><h1 ref={heading} tabIndex={-1}>{mode === "curiosity" ? "What are you curious about?" : "What will you learn today?"}</h1><p>{mode === "curiosity" ? "Explore any topic or language with a question. Your explorations do not change academic progress." : "Start with a question, or choose a topic from My Learning."}</p>{mode === "curiosity" && curiositySuggestions.length > 0 && <div className="curiosity-suggestions">{curiositySuggestions.map(question => <button key={question} onClick={() => { setDraft(activeId, question); document.getElementById("flame-prompt")?.focus(); }}>{question}</button>)}</div>}</section> : <div className="conversation-title-row"><h1 className="request-heading" ref={heading} tabIndex={-1}>{currentShortcut?.title ?? "Your learning request"}</h1>{conversationPin}</div>}
      {session.turns.length > 0 && <FlameConversation turns={session.turns} pending={pending} onRetry={sendQuestion} />}
      {!session.turns.length && context?.subtopic?.id === "gravity" && process.env.NODE_ENV === "development" && <section className="development-response" aria-label="Development response preview"><p className="development-label">Development content · Static formatting preview, not an AI response</p><LearningContent blocks={gravityDevelopmentContent} /><ResourceRecommendations key={activeId} resources={gravityDevelopmentResources} /></section>}
    </ConversationViewport>
    <FlamePromptInput key={activeId} responseLanguage={responseLanguage} onResponseLanguageChange={chooseResponseLanguage} attachments={session.attachments} attachmentNotice={session.attachmentNotice} onFiles={files => addFiles(activeId, files)} onRemoveAttachment={id => removeAttachment(activeId, id)} topicName={context?.subtopic?.name ?? context?.topic.name} value={session.draft} pending={pending || loadingHistory || Boolean(live && mode === "study" && resumed && !context)} onValueChange={draft => setDraft(activeId, draft)} onSubmit={() => sendQuestion()} />
    {libraryOpen && <LearningLibrary live={live} catalogue={live ? catalogue : undefined} onRemoveCurriculum={(id, after) => requestRemoval(id, undefined, undefined, after)} onRemoveSubject={(id, levelId, subjectId, after) => requestRemoval(id, levelId, subjectId, after)} learning={learning} onAdd={addLearning} onClose={() => setLibraryOpen(false)} />}
    {removal && <RemovalConfirmation name={removal.subject?.name ?? removal.curriculum.name} kind={removal.subject ? "subject" : "curriculum"} context={removal.subject ? `${removal.curriculum.name} / ${removal.curriculum.levels.find(l => l.id === removal.levelId)?.name ?? ""}` : undefined} onCancel={() => setRemoval(null)} onConfirm={confirmRemoval} />}
  </StudentAppShell>}</ExploreWorkspace>;
}




