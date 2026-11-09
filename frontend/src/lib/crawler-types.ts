export const BOGAZICI_REQUESTED_SEED = "https://www.bogazici.edu.tr/";
export const BOGAZICI_SEED = "https://bogazici.edu.tr/";
export const DEFAULT_SEED = BOGAZICI_SEED;
export const REQUESTED_SEED = "https://www.tsk.gov.tr/";
export const OFFICIAL_SEED = "https://www.tsk.tr/";
export const OFFICIAL_SOURCE_URL = "https://www.turkiye.gov.tr/genelkurmay-baskanligi";
export const MIN_PAGE_LIMIT = 1;
export const DEFAULT_PAGE_LIMIT = 200;

export type CrawlPhase = "idle" | "running" | "paused" | "completed" | "blocked" | "error" | "limit_reached";
export type CrawlAction = "start" | "pause" | "resume" | "retry" | "set_limit" | "reset";
export type LiveMatchSource = "content" | "title" | "url";

export type LiveSearchResult = {
  url: string;
  title: string;
  description: string;
  rank: number;
  indexedAt: string;
  matchSources: LiveMatchSource[];
};

export type CrawlStatus = {
  ok: true;
  seed: string;
  status: CrawlPhase;
  indexedPages: number;
  queuedPages: number;
  visitedPages: number;
  failedPages: number;
  skippedPages: number;
  indexedWords: number;
  linkCount: number;
  maxPages: number;
  maxDepth: number;
  delayMs: number;
  currentUrl: string | null;
  lastError: string | null;
  updatedAt: string | null;
  startedAt: string | null;
  lastIndexedAt: string | null;
  revision: number;
  recentPages: { url: string; title: string; indexedAt: string }[];
  recentErrors: { url: string; error: string }[];
};

export type LiveSearchResponse = {
  ok: true;
  startedAt: string | null;
  query: string;
  results: LiveSearchResult[];
  total: number;
  tookMs: number;
  indexedPages: number;
  revision: number;
  status: CrawlPhase;
};

export type LiveExplorerResponse = {
  ok: true;
  seed: string;
  startedAt: string | null;
  status: CrawlPhase;
  revision: number;
  updatedAt: string | null;
  graph: Record<string, string[]>;
  pages: Record<string, { title: string; description: string; indexedAt: string; rank: number }>;
  stats: {
    pages: number;
    links: number;
    discoveredLinks: number;
    words: number;
    queued: number;
  };
};

export type LiveWordsResponse = {
  ok: true;
  seed: string;
  startedAt: string | null;
  revision: number;
  query: string;
  total: number;
  offset: number;
  limit: number;
  entries: { word: string; pageCount: number; pages: { url: string; title: string }[] }[];
};
