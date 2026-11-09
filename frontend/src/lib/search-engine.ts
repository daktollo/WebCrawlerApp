export type Graph = Record<string, string[]>;

export type Dataset = {
  name: string;
  origin: "sample" | "import" | "live";
  index: Record<string, string[]>;
  graph: Graph;
  pages?: Record<string, { title?: string; description?: string }>;
};

export type SearchMatchSource = "index" | "title" | "url";

export type SearchResult = {
  url: string;
  title: string;
  description: string;
  rank: number;
  incoming: number;
  outgoing: number;
  matchSources?: SearchMatchSource[];
};

export const COLAB_URL =
  "https://colab.research.google.com/drive/1Pl_Vxa5JpJfEfWWs0gBGWVkeCTI1F6bm";

export const COLAB_EXPORT_CODE = `import json
from google.colab import files

data = {
    "index": index1,
    "graph": graph1,
    "ranks": computeRanks(graph1),
}

file_name = "dijital_vatan_verileri.json"
with open(file_name, "w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

files.download(file_name)`;

const HOME = "https://searchengineplaces.com.tr/";
const BASE = "http://www.searchengineplaces.com.tr/";
const page = (path: string) => BASE + path;

// Source: Question 1's saved graph and assertions in the original DSAI 301
// Summer 2025 Final Exam Answer Key. Only three keyword memberships are known.
// Titles are display labels; descriptions explain graph relationships, not
// quotations or snippets from the historical website's unavailable HTML.
export const SAMPLE_DATASET: Dataset = {
  name: "Search Engine Places",
  origin: "sample",
  graph: {
    [HOME]: [page("travel_guide.html")],
    [page("travel_guide.html")]: [
      page("ankara.html"),
      page("konya.html"),
      page("istanbul.html"),
      page("oktayrecommends.html"),
      page("seymarecommends.html"),
    ],
    [page("seymarecommends.html")]: [
      page("oktayrecommends.html"),
      page("konya.html"),
    ],
    [page("oktayrecommends.html")]: [page("istanbul.html")],
    [page("istanbul.html")]: [
      page("maidens_tower.html"),
      page("galata_tower.html"),
    ],
    [page("galata_tower.html")]: [
      page("istanbul.html"),
      page("travel_guide.html"),
    ],
    [page("maidens_tower.html")]: [
      page("istanbul.html"),
      page("travel_guide.html"),
    ],
    [page("konya.html")]: [
      page("seymarecommends.html"),
      page("mevlana.html"),
    ],
    [page("mevlana.html")]: [page("travel_guide.html")],
    [page("ankara.html")]: [],
  },
  index: {
    Our: [HOME, page("travel_guide.html")],
    learn: [HOME, page("istanbul.html"), page("mevlana.html")],
    in: [
      page("travel_guide.html"),
      page("istanbul.html"),
      page("galata_tower.html"),
      page("maidens_tower.html"),
      page("konya.html"),
      page("mevlana.html"),
    ],
  },
  pages: {
    [HOME]: {
      title: "Search Engine Places",
      description:
        "Taramanın başlangıç sayfası. Bağlantı grafiğinde seyahat rehberine yönelir.",
    },
    [page("travel_guide.html")]: {
      title: "Seyahat rehberi",
      description:
        "Ankara, Konya, İstanbul ve iki öneri sayfasını bir araya getiren bağlantı noktası.",
    },
    [page("seymarecommends.html")]: {
      title: "Şeyma'nın önerileri",
      description:
        "Bağlantı grafiğinde Konya'ya ve Oktay'ın önerilerine yönelen sayfa.",
    },
    [page("oktayrecommends.html")]: {
      title: "Oktay'ın önerileri",
      description:
        "Seyahat rehberi ve Şeyma'nın önerilerinden bağlantı alır; İstanbul'a yönelir.",
    },
    [page("istanbul.html")]: {
      title: "İstanbul",
      description:
        "Galata Kulesi ve Kız Kulesi sayfalarına bağlanır. Bu iki sayfa da İstanbul'a geri bağlantı verir.",
    },
    [page("galata_tower.html")]: {
      title: "Galata Kulesi",
      description:
        "İstanbul sayfasından bağlantı alır; İstanbul ve seyahat rehberine yönelir.",
    },
    [page("maidens_tower.html")]: {
      title: "Kız Kulesi",
      description:
        "İstanbul sayfasından bağlantı alır; İstanbul ve seyahat rehberine yönelir.",
    },
    [page("konya.html")]: {
      title: "Konya",
      description:
        "Mevlana ve Şeyma'nın önerileri sayfalarına giden iki bağlantıya sahiptir.",
    },
    [page("mevlana.html")]: {
      title: "Mevlana",
      description:
        "Konya sayfasından bağlantı alır ve seyahat rehberine yönelir.",
    },
    [page("ankara.html")]: {
      title: "Ankara",
      description:
        "Seyahat rehberinden bağlantı alır. Kaynak grafikte dışarıya verdiği bağlantı bulunmaz.",
    },
  },
};

function dictionary<T>(): Record<string, T> {
  return Object.create(null) as Record<string, T>;
}

function owns(object: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(object, key);
}

// Match the teaching implementation, including its treatment of dangling nodes.
// Repeated outlinks count in the denominator, but each source contributes once
// to a destination, exactly like Python's `if page in graph[node]` condition.
export function computeRanks(
  graph: Graph,
  damping = 0.8,
  iterations = 10,
): Record<string, number> {
  if (!Number.isFinite(damping) || damping < 0 || damping > 1) {
    throw new Error("PageRank katsayısı 0 ile 1 arasında olmalıdır.");
  }
  if (!Number.isInteger(iterations) || iterations < 0 || iterations > 1000) {
    throw new Error("İterasyon sayısı 0 ile 1000 arasında bir tam sayı olmalıdır.");
  }

  const urls = Object.keys(graph);
  let ranks = dictionary<number>();
  if (urls.length === 0) return ranks;

  const incoming = dictionary<string[]>();
  for (const url of urls) {
    ranks[url] = 1 / urls.length;
    incoming[url] = [];
  }
  for (const source of urls) {
    for (const target of new Set(graph[source])) {
      if (owns(incoming, target)) incoming[target].push(source);
    }
  }

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const next = dictionary<number>();
    for (const url of urls) {
      let rank = (1 - damping) / urls.length;
      for (const source of incoming[url]) {
        rank += damping * (ranks[source] / graph[source].length);
      }
      next[url] = rank;
    }
    ranks = next;
  }
  return ranks;
}

export function getPageInfo(
  url: string,
  dataset: Dataset,
): { title: string; description: string; category: string } {
  const details = dataset.pages && owns(dataset.pages, url) ? dataset.pages[url] : undefined;
  let title = url;
  let category = "Web sayfası";
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.split("/").filter(Boolean).pop();
    if (!path) {
      title = parsed.hostname.replace(/^www\./, "");
      category = "Ana sayfa";
    } else {
      let readable = path.replace(/\.(html?|php|aspx?)$/i, "");
      try {
        readable = decodeURIComponent(readable);
      } catch {
        // A malformed percent escape should not prevent a URL from rendering.
      }
      title = readable.replace(/[_-]+/g, " ");
      title = title.charAt(0).toLocaleUpperCase("tr-TR") + title.slice(1);
    }
    if (dataset.origin === "sample") {
      if (["istanbul.html", "ankara.html", "konya.html"].includes(path ?? "")) {
        category = "Şehir";
      } else if (path === "travel_guide.html") {
        category = "Rehber";
      } else if (path?.endsWith("recommends.html")) {
        category = "Öneriler";
      } else if (path) {
        category = "Yer";
      }
    }
  } catch {
    // Imported URLs are validated by parseDataset; keep this helper total.
  }

  const outlinks = owns(dataset.graph, url) ? dataset.graph[url].length : 0;
  const incoming = Object.values(dataset.graph).filter((links) => links.includes(url)).length;
  return {
    title: details?.title || title,
    description:
      details?.description ||
      `Bu sayfa ${incoming} sayfadan bağlantı alıyor ve ${outlinks} bağlantı veriyor.`,
    category,
  };
}

function foldSearchText(value: string): string {
  // Preserve accents while treating composed/decomposed text identically.
  // JavaScript lowercases capital İ to i + combining dot; fold that pair to i
  // so İstanbul/istanbul also work without applying Turkish casing to English.
  return value.normalize("NFC").toLowerCase().replace(/i\u0307/g, "i").normalize("NFC");
}

function searchTokens(value: string, caseSensitive: boolean): string[] {
  const normalized = caseSensitive ? value.normalize("NFC") : foldSearchText(value);
  return normalized.match(/[\p{L}\p{N}]+/gu) ?? [];
}

function containsPhrase(tokens: string[], phrase: string[]): boolean {
  if (phrase.length === 0 || phrase.length > tokens.length) return false;
  for (let start = 0; start <= tokens.length - phrase.length; start += 1) {
    if (phrase.every((token, offset) => token === tokens[start + offset])) return true;
  }
  return false;
}

function searchableUrl(url: string): string {
  try {
    const parsed = new URL(url);
    let path = parsed.pathname;
    try {
      path = decodeURIComponent(path);
    } catch {
      // Malformed percent escapes should not stop searching other URL tokens.
      path = path.replace(/(?:%[\da-fA-F]{2})+/g, (part) => {
        try { return decodeURIComponent(part); } catch { return part; }
      });
    }
    // Query parameters and fragments are deliberately outside this search scope.
    return `${parsed.hostname} ${path}`;
  } catch {
    return "";
  }
}

export function searchDataset(
  dataset: Dataset,
  query: string,
  caseSensitive = false,
  damping = 0.8,
  iterations = 10,
  includePageMetadata = true,
): SearchResult[] {
  const keyword = query.trim();
  if (!keyword) return [];

  // Keep content-index matches exact. Title/URL matches have their own source
  // labels; authored graph descriptions never become searchable page content.
  const matches = new Map<string, Set<SearchMatchSource>>();
  const addMatch = (url: string, source: SearchMatchSource) => {
    if (!owns(dataset.graph, url)) return;
    const sources = matches.get(url) ?? new Set<SearchMatchSource>();
    sources.add(source);
    matches.set(url, sources);
  };
  if (caseSensitive) {
    if (owns(dataset.index, keyword)) {
      for (const url of dataset.index[keyword]) addMatch(url, "index");
    }
  } else {
    const folded = foldSearchText(keyword);
    for (const [word, urls] of Object.entries(dataset.index)) {
      if (foldSearchText(word) === folded) {
        for (const url of urls) addMatch(url, "index");
      }
    }
  }

  if (includePageMetadata) {
    const phrase = searchTokens(keyword, caseSensitive);
    for (const url of Object.keys(dataset.graph)) {
      if (containsPhrase(searchTokens(getPageInfo(url, dataset).title, caseSensitive), phrase)) {
        addMatch(url, "title");
      }
      if (containsPhrase(searchTokens(searchableUrl(url), caseSensitive), phrase)) {
        addMatch(url, "url");
      }
    }
  }
  if (matches.size === 0) return [];

  const ranks = computeRanks(dataset.graph, damping, iterations);
  const results: SearchResult[] = [];
  for (const [url, sources] of matches) {
    const info = getPageInfo(url, dataset);
    results.push({
      url,
      title: info.title,
      description: info.description,
      rank: ranks[url],
      incoming: Object.values(dataset.graph).filter((links) => links.includes(url)).length,
      outgoing: dataset.graph[url].length,
      matchSources: [...sources],
    });
  }
  // Stable sorting preserves index order for equal scores; metadata-only pages
  // follow in graph order without changing the notebook's PageRank formula.
  return results.sort((left, right) => right.rank - left.rank);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function validUrl(value: unknown): value is string {
  if (
    typeof value !== "string" ||
    value.length > 4096 ||
    /\s|[\u0000-\u001f\u007f]/.test(value) ||
    !/^https?:\/\//i.test(value)
  ) {
    return false;
  }
  try {
    const parsed = new URL(value);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.hostname.length > 0 &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}

export function parseDataset(raw: unknown, fileName?: string): Dataset {
  if (!isRecord(raw) || !isRecord(raw.graph) || !isRecord(raw.index)) {
    throw new Error('JSON dosyası "graph" ve "index" adlı iki sözlük içermelidir.');
  }

  const graphEntries = Object.entries(raw.graph);
  if (graphEntries.length === 0) {
    throw new Error("Bağlantı grafiği boş olamaz. Önce Colab defterinde taramayı çalıştırın.");
  }
  if (graphEntries.length > 500) {
    throw new Error("Bir veri kümesinde en fazla 500 sayfa bulunabilir.");
  }

  const graph = dictionary<string[]>();
  let linkCount = 0;
  for (const [url, links] of graphEntries) {
    if (!validUrl(url)) {
      throw new Error("Grafikteki her sayfa adresi geçerli bir http veya https URL'si olmalıdır.");
    }
    if (!Array.isArray(links)) {
      throw new Error("Grafikte her sayfanın bağlantıları bir liste olarak verilmelidir.");
    }
    linkCount += links.length;
    if (linkCount > 50_000) {
      throw new Error("Bağlantı grafiğinde en fazla 50.000 bağlantı bulunabilir.");
    }
    if (!links.every(validUrl)) {
      throw new Error("Grafikte geçersiz bir bağlantı adresi var. Yalnızca http ve https adresleri kabul edilir.");
    }
    graph[url] = [...links];
  }
  for (const links of Object.values(graph)) {
    if (links.some((url) => !owns(graph, url))) {
      throw new Error("Her bağlantının hedefi grafikte bir sayfa olarak yer almalıdır.");
    }
  }

  const indexEntries = Object.entries(raw.index);
  if (indexEntries.length > 100_000) {
    throw new Error("Kelime indeksinde en fazla 100.000 kelime bulunabilir.");
  }
  const index = dictionary<string[]>();
  for (const [word, urls] of indexEntries) {
    if (word.length === 0 || word.length > 4096) {
      throw new Error("İndeksteki kelimeler boş olmamalı ve 4096 karakteri aşmamalıdır.");
    }
    if (!Array.isArray(urls) || urls.length > 50_000) {
      throw new Error("Her kelimenin sayfa adresleri en fazla 50.000 öğeli bir liste olmalıdır.");
    }
    if (!urls.every(validUrl) || urls.some((url) => !owns(graph, url))) {
      throw new Error("İndeksteki her URL, bağlantı grafiğinde bulunan geçerli bir sayfa olmalıdır.");
    }
    // Null-prototype dictionaries keep keywords such as __proto__ harmless.
    index[word] = [...new Set<string>(urls)];
  }

  let pages: Dataset["pages"];
  if (raw.pages !== undefined) {
    if (!isRecord(raw.pages)) {
      throw new Error('İsteğe bağlı "pages" alanı bir sözlük olmalıdır.');
    }
    const pageEntries = Object.entries(raw.pages);
    if (pageEntries.length > 500) {
      throw new Error("Sayfa bilgilerinde en fazla 500 kayıt bulunabilir.");
    }
    pages = dictionary<{ title?: string; description?: string }>();
    for (const [url, details] of pageEntries) {
      if (!validUrl(url) || !owns(graph, url) || !isRecord(details)) {
        throw new Error("Sayfa bilgileri grafikte bulunan URL'lere ait başlık ve açıklama nesneleri olmalıdır.");
      }
      const info: { title?: string; description?: string } = {};
      if (details.title !== undefined) {
        if (typeof details.title !== "string" || details.title.length > 300) {
          throw new Error("Sayfa başlıkları en fazla 300 karakterlik metinler olmalıdır.");
        }
        info.title = details.title.trim();
      }
      if (details.description !== undefined) {
        if (typeof details.description !== "string" || details.description.length > 2000) {
          throw new Error("Sayfa açıklamaları en fazla 2000 karakterlik metinler olmalıdır.");
        }
        info.description = details.description.trim();
      }
      pages[url] = info;
    }
  }

  const fallbackName = fileName?.split(/[\\/]/).pop()?.replace(/\.json$/i, "").trim();
  const name = typeof raw.name === "string" && raw.name.trim() ? raw.name.trim() : fallbackName;
  return {
    name: (name || "Colab veri kümesi").slice(0, 160),
    origin: "import",
    index,
    graph,
    ...(pages ? { pages } : {}),
  };
}

export function datasetStats(dataset: Dataset): {
  pages: number;
  links: number;
  words: number;
} {
  return {
    pages: Object.keys(dataset.graph).length,
    links: Object.values(dataset.graph).reduce((total, links) => total + links.length, 0),
    words: Object.keys(dataset.index).length,
  };
}
