export type Proficiency = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;
export type LearningStatus = "not-started" | "in-progress" | "review-due" | "mastered";

export interface Subtopic {
  id: string;
  name: string;
  description: string | null;
  proficiency: Proficiency | null;
  status: LearningStatus | null;
  locked?: boolean;
  lockReason?: string;
}
export interface Topic { id: string; name: string; categoryId: string | null; subtopics: Subtopic[] }
export interface Domain { id: string; name: string; progress: number | null; topics: Topic[] }
export interface Subject { id: string; name: string; progress: number | null; domains: Domain[] }
export interface Level { id: string; name: string; progress: number | null; subjects: Subject[] }
export interface Curriculum { id: string; name: string; revision?: number; progress: number | null; levels: Level[] }

export interface TopicContext {
  curriculum: Curriculum;
  level: Level;
  subject: Subject;
  domain: Domain;
  topic: Topic;
  subtopic?: Subtopic;
}
export interface LearningContext {
  curriculumId: string;
  levelId: string;
  subjectId: string;
  domainId: string;
  categoryId: string | null;
  topicId: string;
  subtopicId: string | null;
}
