
import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowRight, ArrowUpRight, Check, ChevronLeft, ChevronRight, Clock3, Database, Download, ExternalLink, FileText, Globe2, Hash, Info, Link2, LoaderCircle, Network, RefreshCw, Search, Settings2 } from "lucide-react";
import { NetworkGraph } from "@/components/network-graph";
import type { CrawlStatus, LiveExplorerResponse, LiveWordsResponse } from "@/lib/crawler-types";
import type { Dataset } from "@/lib/search-engine";

type ExplorerView = "graph" | "index" | "data";
type Props = {
  view: ExplorerView;
  status: CrawlStatus | null;
  onSearch: (word: string) => void;
  onOpenSample: () => void;
  onViewChange: (view: ExplorerView) => void;
  onManageCrawl: () => void;
  requestedNode?: { url: string; nonce: number } | null;
};

const WORD_PAGE_SIZE = 50;
const PAGE_LIST_SIZE = 30;
const PHASE_LABELS: Record<CrawlStatus["status"], string> = {
  idle: "Tarama bekleniyor", running: "Tarama sürüyor", paused: "Tarama duraklatıldı",
  completed: "Tarama tamamlandı", blocked: "Kaynak erişimi engellendi", error: "Kaynağa ulaşılamadı",
  limit_reached: "Sayfa sınırına ulaşıldı",
};

function number(value: number) { return value.toLocaleString("tr-TR"); }
function rank(value: number) { return value.toLocaleString("tr-TR", { minimumFractionDigits: 6, maximumFractionDigits: 6 }); }
function shortUrl(value: string) { return value.replace(/^https?:\/\//, "").replace(/\/$/, ""); }
function fold(value: string) { return value.normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g, "").replace(/ı/g, "i"); }
function date(value: string | null) {
  if (!value) return "Henüz yok";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function safeHref(value: string) {
  try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : "#"; }
  catch { return "#"; }
}

async function readApi<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, cache: "no-store", credentials: "same-origin" });
  let value: unknown;
  try { value = await response.json(); } catch { throw new Error("Sunucudan beklenen veri alınamadı. Yeniden deneyin."); }
  if (!response.ok || !value || typeof value !== "object" || !("ok" in value) || !value.ok) {
    throw new Error(value && typeof value === "object" && "error" in value && typeof value.error === "string" ? value.error : "Canlı indeks şu anda alınamıyor.");
  }
  return value as T;
}

function Pager({ offset, limit, total, loading = false, onPage }: { offset: number; limit: number; total: number; loading?: boolean; onPage: (offset: number) => void }) {
  return <div className="le-pagination"><span>{total ? `${number(offset + 1)}–${number(Math.min(offset + limit, total))} / ${number(total)}` : "0 kayıt"}</span><div>
    <button type="button" className="secondary-button" aria-label="Önceki sayfa" disabled={offset === 0 || loading} onClick={() => onPage(Math.max(0, offset - limit))}><ChevronLeft size={15}/>Önceki</button>
    <button type="button" className="secondary-button" aria-label="Sonraki sayfa" disabled={offset + limit >= total || loading} onClick={() => onPage(offset + limit)}>Sonraki<ChevronRight size={15}/></button>
  </div></div>;
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="le-empty"><span><Database size={25}/></span><h2>{title}</h2><p>{detail}</p></div>;
}

function PageCatalog({ snapshot, selectedUrl, onPick }: { snapshot: LiveExplorerResponse; selectedUrl: string | null; onPick: (url: string) => void }) {
  const [filter, setFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const entries = useMemo(() => Object.entries(snapshot.pages).map(([url, page]) => ({ url, ...page })).sort((a, b) => b.rank - a.rank || a.title.localeCompare(b.title, "tr") || a.url.localeCompare(b.url)), [snapshot.pages]);
  const filtered = useMemo(() => {
    const query = fold(filter.trim());
    return query ? entries.filter(page => fold(`${page.title} ${page.url}`).includes(query)) : entries;
  }, [entries, filter]);
  const safeOffset = Math.min(offset, Math.max(0, (Math.ceil(filtered.length / PAGE_LIST_SIZE) - 1) * PAGE_LIST_SIZE));
  useEffect(() => { setFilter(""); setOffset(0); }, [snapshot.seed]);
  return <section className="le-page-catalog" aria-labelledby="le-pages-title"><div className="le-catalog-head"><div><h2 id="le-pages-title"><FileText size={17}/>İndekslenen sayfalar</h2><p>Tüm sayfalara bu listeden ulaşabilir, haritada seçebilirsiniz.</p></div><label className="le-filter"><Search size={17}/><input aria-label="Canlı sayfalarda filtrele" placeholder="Başlık veya adres ara..." value={filter} onChange={event => { setFilter(event.target.value); setOffset(0); }}/></label></div>
    <div className="le-table-wrap"><table className="le-pages-table"><thead><tr><th>SAYFA</th><th>PAGERANK</th><th>SON İNDEKSLEME</th><th><span className="sr-only">Haritada göster</span></th></tr></thead><tbody>{filtered.slice(safeOffset, safeOffset + PAGE_LIST_SIZE).map(page => <tr key={page.url} className={selectedUrl === page.url ? "le-selected-row" : undefined}><td><button type="button" className="le-page-title" onClick={() => onPick(page.url)}>{page.title || shortUrl(page.url)}</button><a href={safeHref(page.url)} target="_blank" rel="noopener noreferrer" className="le-page-address">{shortUrl(page.url)}<ExternalLink size={11}/></a></td><td className="le-tabular">{rank(page.rank)}</td><td><time dateTime={page.indexedAt}>{date(page.indexedAt)}</time></td><td><button type="button" className="icon-button" aria-label={`${page.title || shortUrl(page.url)} sayfasını haritada göster`} onClick={() => onPick(page.url)}><Network size={17}/></button></td></tr>)}</tbody></table></div>
    {!filtered.length && <p className="le-table-empty">Bu filtreyle eşleşen sayfa bulunamadı.</p>}
    <Pager offset={safeOffset} limit={PAGE_LIST_SIZE} total={filtered.length} onPage={setOffset}/>
  </section>;
}

export function LiveExplorer({ view, status, onSearch, onOpenSample, onViewChange, onManageCrawl, requestedNode }: Props) {
  const seed = status?.seed ?? null;
  const startedAt = status?.startedAt ?? null;
  const runKey = JSON.stringify([seed, startedAt]);
  const latestRun = useRef(runKey);
  latestRun.current = runKey;
  const [snapshot, setSnapshot] = useState<LiveExplorerResponse | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
  const [wordFilter, setWordFilter] = useState("");
  const [debouncedFilter, setDebouncedFilter] = useState("");
  const [wordOffset, setWordOffset] = useState(0);
  const [wordResult, setWordResult] = useState<{ key: string; value: LiveWordsResponse } | null>(null);
  const [wordsLoading, setWordsLoading] = useState(false);
  const [wordsError, setWordsError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);
  const data = snapshot?.seed === seed && snapshot.startedAt === startedAt ? snapshot : null;
  const wordKey = JSON.stringify([runKey, debouncedFilter, wordOffset]);
  const words = wordResult?.key === wordKey && wordResult.value.seed === seed && wordResult.value.startedAt === startedAt ? wordResult.value : null;

  useEffect(() => {
    setSnapshot(null); setSnapshotError(null); setSnapshotLoading(true);
    setSelectedUrl(null); setWordFilter(""); setDebouncedFilter(""); setWordOffset(0);
    setWordResult(null); setWordsError(null); setDownloaded(false);
  }, [seed, startedAt]);

  useEffect(() => {
    if (requestedNode) setSelectedUrl(requestedNode.url);
  }, [requestedNode?.url, requestedNode?.nonce]);

  // A crawl revision can advance faster than a large snapshot can finish.
  // Poll at a bounded interval instead of aborting/restarting each revision.
  useEffect(() => {
    if (status?.status !== "running") return;
    const timer = setInterval(() => setRefreshTick(value => value + 1), 15000);
    return () => clearInterval(timer);
  }, [status?.status]);

  useEffect(() => {
    if (!seed) return;
    let stopped = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    setSnapshotLoading(true); setSnapshotError(null);
    void readApi<LiveExplorerResponse>(`/api/crawl/explorer?seed=${encodeURIComponent(seed)}`, controller.signal)
      .then(next => {
        if (next.seed !== seed || next.startedAt !== startedAt) throw new Error("Tarama yenilendi. Güncel veriye bağlanılıyor.");
        if (!stopped && latestRun.current === runKey) setSnapshot(previous => previous?.seed === seed && previous.startedAt === startedAt && previous.revision > next.revision ? previous : next);
      })
      .catch(error => { if (!stopped && latestRun.current === runKey) setSnapshotError(error instanceof Error && error.name !== "AbortError" ? error.message : "Canlı indeks yanıtı gecikti. Yeniden deneyin."); })
      .finally(() => { clearTimeout(timeout); if (!stopped && latestRun.current === runKey) setSnapshotLoading(false); });
    return () => { stopped = true; clearTimeout(timeout); controller.abort(); };
  }, [seed, startedAt, runKey, refreshTick, refresh, status?.status]);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedFilter(wordFilter.trim()); setWordOffset(0); }, 250);
    return () => clearTimeout(timer);
  }, [wordFilter]);

  useEffect(() => {
    if (view !== "index" || !seed) return;
    let stopped = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    setWordsLoading(true); setWordsError(null);
    const params = new URLSearchParams({ q: debouncedFilter, offset: String(wordOffset), limit: String(WORD_PAGE_SIZE), seed });
    void readApi<LiveWordsResponse>(`/api/crawl/words?${params}`, controller.signal)
      .then(next => {
        if (next.seed !== seed || next.startedAt !== startedAt) throw new Error("Tarama yenilendi. Kelime indeksi güncelleniyor.");
        if (!stopped && latestRun.current === runKey) {
          if (wordOffset > 0 && wordOffset >= next.total) setWordOffset(Math.max(0, (Math.ceil(next.total / WORD_PAGE_SIZE) - 1) * WORD_PAGE_SIZE));
          else setWordResult(previous => previous?.key === wordKey && previous.value.revision > next.revision ? previous : { key: wordKey, value: next });
        }
      })
      .catch(error => { if (!stopped && latestRun.current === runKey) setWordsError(error instanceof Error && error.name !== "AbortError" ? error.message : "Kelime indeksi yanıtı gecikti. Yeniden deneyin."); })
      .finally(() => { clearTimeout(timeout); if (!stopped && latestRun.current === runKey) setWordsLoading(false); });
    return () => { stopped = true; clearTimeout(timeout); controller.abort(); };
  }, [view, seed, startedAt, runKey, refreshTick, debouncedFilter, wordOffset, wordKey, refresh, status?.status]);

  const dataset: Dataset = useMemo(() => ({
    name: data ? `${shortUrl(data.seed)} başlangıçlı tarama` : "Canlı indeks", origin: "live", index: {},
    graph: data?.graph ?? {}, pages: data?.pages ?? {},
  }), [data]);
  const ranks = useMemo(() => Object.fromEntries(Object.entries(data?.pages ?? {}).map(([url, page]) => [url, page.rank])), [data]);
  const rankedUrls = useMemo(() => Object.keys(dataset.graph).sort((a, b) => (ranks[b] || 0) - (ranks[a] || 0) || a.localeCompare(b)), [dataset.graph, ranks]);
  const currentNode = selectedUrl && Object.hasOwn(dataset.graph, selectedUrl) ? selectedUrl : rankedUrls[0] ?? null;
  const node = currentNode ? data?.pages[currentNode] : null;
  const incoming = useMemo(() => currentNode ? Object.keys(dataset.graph).filter(url => dataset.graph[url].includes(currentNode)) : [], [dataset.graph, currentNode]);
  const outgoing = currentNode ? dataset.graph[currentNode] ?? [] : [];

  function pickNode(url: string) { setSelectedUrl(url); onViewChange("graph"); }
  function downloadGraph() {
    if (!data) return;
    const exportData = { name: `${shortUrl(data.seed)} başlangıçlı tarama`, seed: data.seed, exportedAt: new Date().toISOString(), indexedAt: data.updatedAt, revision: data.revision, graph: data.graph, pages: data.pages, ranks, stats: data.stats };
    const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = objectUrl; link.download = "dijital_vatan_canli_baglantilar.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000); setDownloaded(true);
  }

  const heading = view === "graph" ? "Canlı bağlantı haritası." : view === "index" ? "Canlı kelime indeksi." : "Canlı veri kümesi.";
  const description = view === "graph" ? "Taranan sayfaları ve aralarındaki bağlantıları keşfedin." : view === "index" ? "İndekslenen kelimeleri ve bu kelimelerin geçtiği sayfaları inceleyin." : "Aramanın, haritanın ve kelime indeksinin kullandığı güncel veriler.";

  return <section className="le-root" aria-labelledby="le-title">
    <div className="section-heading le-heading"><div><span className="hero-eyebrow">CANLI WEB İNDEKSİ</span><h1 id="le-title">{heading}</h1><p>{description}</p></div><div className="le-heading-actions">{status && <button type="button" className="secondary-button" onClick={onManageCrawl}><Settings2 size={15}/>Tarama ayarları</button>}<button type="button" className="secondary-button" disabled={snapshotLoading} onClick={() => setRefresh(value => value + 1)}>{snapshotLoading ? <LoaderCircle className="lc-spin" size={15}/> : <RefreshCw size={15}/>}Yenile</button></div></div>
    <div className="le-source-bar"><span className="le-source-label"><span className={status?.status === "running" ? "le-active-dot" : ""}/>{seed ? <a href={safeHref(seed)} target="_blank" rel="noopener noreferrer">Başlangıç: {shortUrl(seed)}<ArrowUpRight size={13}/></a> : "Başlangıç adresi yükleniyor"}</span><div><span>{status ? PHASE_LABELS[status.status] : "Bağlanılıyor"}</span>{data && <span><Clock3 size={12}/>Veri güncellemesi: <time dateTime={data.updatedAt ?? undefined}>{date(data.updatedAt)}</time></span>}{snapshotLoading && data && <span className="le-updating"><LoaderCircle size={12} className="lc-spin"/>Güncelleniyor</span>}</div></div>
    {snapshotError && <div className="le-alert" role="alert"><AlertCircle size={17}/><p>{snapshotError}{data && " Son alınan veriler gösteriliyor."}</p><button type="button" onClick={() => setRefresh(value => value + 1)}>Yeniden dene</button></div>}
    {!data ? <div className="le-loading" role="status">{!snapshotError ? <><LoaderCircle size={27} className="lc-spin"/><strong>Canlı indekse bağlanılıyor</strong><p>Harita ve tablolar güncel tarama verilerinden hazırlanıyor.</p></> : <><Database size={27}/><strong>Canlı veri yüklenemedi</strong><p>Bağlantı yeniden kurulduğunda veriler burada görünecek.</p></>}</div> : <>
      <div className="le-stats" aria-label="Canlı veri özeti"><div><FileText size={18}/><span><strong>{number(data.stats.pages)}</strong>indekslenen sayfa</span></div><div><Link2 size={18}/><span><strong>{number(data.stats.links)}</strong>harita bağlantısı</span></div><div><Hash size={18}/><span><strong>{number(data.stats.words)}</strong>indekslenen kelime</span></div><div><Database size={18}/><span><strong>{number(data.stats.queued)}</strong>kuyruktaki adres</span></div></div>

      {view === "graph" && (data.stats.pages ? <><div className="graph-workspace le-graph-workspace"><section className="large-graph-card"><div className="card-heading"><h2><Network size={16}/>Canlı bağlantı haritası</h2><span className="tiny-badge">{number(data.stats.pages)} sayfa · {number(data.stats.links)} bağlantı</span></div><NetworkGraph dataset={dataset} ranks={ranks} selectedUrl={currentNode} onSelect={setSelectedUrl}/><div className="graph-note"><Info size={15}/><span>Harita, indekslenen sayfalar arasındaki bağlantıları gösterir. Kuyruktaki adresler henüz haritada yer almaz. Daire boyutları canlı aramayla aynı PageRank puanını kullanır.</span></div></section><aside className="node-card le-node-card" aria-label="Seçili canlı sayfa">{currentNode && node && <><span className="section-kicker">SEÇİLİ SAYFA</span><div className="node-title"><span className="page-icon"><Globe2 size={22}/></span><h2>{node.title || shortUrl(currentNode)}</h2></div><a className="node-url" href={safeHref(currentNode)} target="_blank" rel="noopener noreferrer">{shortUrl(currentNode)}<ExternalLink size={12}/></a><div className="node-score"><span>Canlı PageRank puanı</span><strong>{rank(node.rank)}</strong></div><div className="node-link-summary"><span><strong>{number(incoming.length)}</strong>Gelen bağlantı</span><span><strong>{number(outgoing.length)}</strong>Giden bağlantı</span></div><div className="le-connections"><h3>Bu sayfaya bağlananlar</h3>{incoming.length ? <div className="le-connection-list">{incoming.map(url => <button type="button" key={url} onClick={() => setSelectedUrl(url)}><span className="connection-dot incoming"/><span>{data.pages[url]?.title || shortUrl(url)}</span><ChevronRight size={13}/></button>)}</div> : <p>İndekslenen sayfalardan gelen bağlantı yok.</p>}<h3>Bu sayfanın bağlantıları</h3>{outgoing.length ? <div className="le-connection-list">{outgoing.map(url => <button type="button" key={url} onClick={() => setSelectedUrl(url)}><span className="connection-dot"/><span>{data.pages[url]?.title || shortUrl(url)}</span><ChevronRight size={13}/></button>)}</div> : <p>İndekslenen başka bir sayfaya bağlantı yok.</p>}</div></>}</aside></div><PageCatalog key={runKey} snapshot={data} selectedUrl={currentNode} onPick={pickNode}/></> : <Empty title="Harita ilk sayfayla oluşacak." detail="Bu taramada henüz indekslenen sayfa yok. Tarama ilerledikçe farklı sitelerdeki sayfalar ve bağlantılar otomatik görünür."/>)}

      {view === "index" && <section className="index-panel le-index-panel"><div className="index-toolbar"><label className="index-search"><Search size={18}/><input aria-label="Canlı indekste kelime filtrele" value={wordFilter} onChange={event => setWordFilter(event.target.value)} placeholder="Örneğin: araştırma" maxLength={200}/></label><span>{wordsLoading ? "Kelimeler güncelleniyor…" : words ? `${number(words.total)} kelime${debouncedFilter ? " eşleşiyor" : ""}` : "Kelimeler yükleniyor…"}</span></div><div className="le-index-note"><Info size={15}/><p>Bu liste indekslenen sayfa içeriklerinden oluşur. Kelimeyi seçerek arama sonuçlarını, sayfayı seçerek haritadaki yerini açabilirsiniz. Kelimeler, aramada kullanılan harf farklarından arındırılmış biçimleriyle gösterilir.</p></div>{wordsError && <div className="le-alert le-alert-inset" role="alert"><AlertCircle size={16}/><p>{wordsError}{words && " Son alınan kelime listesi gösteriliyor."}</p><button type="button" onClick={() => setRefresh(value => value + 1)}>Yeniden dene</button></div>}
        {words ? <><div className="index-table-wrap"><table className="index-table le-words-table"><thead><tr><th>ANAHTAR KELİME</th><th>SAYFA SAYISI</th><th>GEÇTİĞİ SAYFALAR</th><th><span className="sr-only">Canlı aramada aç</span></th></tr></thead><tbody>{words.entries.map(entry => <tr key={entry.word}><td><button type="button" className="index-word" onClick={() => onSearch(entry.word)}><Hash size={14}/>{entry.word}</button></td><td><span className="count-pill">{number(entry.pageCount)}</span></td><td><div className="index-page-list">{entry.pages.slice(0, 3).map(page => <button type="button" key={page.url} onClick={() => pickNode(page.url)}>{page.title || shortUrl(page.url)}</button>)}{entry.pageCount > Math.min(entry.pages.length, 3) && <button type="button" className="le-more-pages" onClick={() => onSearch(entry.word)}>+{number(entry.pageCount - Math.min(entry.pages.length, 3))} sayfa<ArrowRight size={11}/></button>}</div></td><td><button type="button" className="icon-button" aria-label={`${entry.word} kelimesini canlı indekste ara`} onClick={() => onSearch(entry.word)}><ArrowUpRight size={17}/></button></td></tr>)}</tbody></table></div>{!words.entries.length && <p className="le-table-empty">{debouncedFilter ? "Bu filtreyle eşleşen kelime bulunamadı." : "İlk sayfanın kelimeleri indekslendiğinde burada görünecek."}</p>}<Pager offset={words.offset} limit={words.limit} total={words.total} loading={wordsLoading} onPage={setWordOffset}/></> : <div className="le-word-loading" role="status">{wordsLoading ? <><LoaderCircle className="lc-spin" size={20}/>Kelime indeksi yükleniyor</> : "Kelime listesi henüz alınamadı."}</div>}
      </section>}

      {view === "data" && <><section className="le-data-card"><div className="le-data-intro"><span className="le-data-icon"><Database size={24}/></span><div><span className="section-kicker">TARAMANIN BAŞLANGIÇ ADRESİ</span><h2>{shortUrl(data.seed)}</h2><p>Bu adresten bağlantılarla ulaşılan farklı sitelerdeki sayfalar aynı indekste birikir. Canlı arama, bağlantı haritası ve kelime indeksi aynı taramanın güncel verilerini kullanır.</p></div></div><dl className="le-data-details"><div><dt>Tarama kapsamı</dt><dd>Bağlantılarla keşfedilen siteler</dd></div><div><dt>Veri güncellemesi</dt><dd>{date(data.updatedAt)}</dd></div><div><dt>İndekslenen sayfalar arasındaki bağlantılar</dt><dd>{number(data.stats.links)}</dd></div><div><dt>Sayfalarda keşfedilen toplam bağlantı</dt><dd>{number(data.stats.discoveredLinks)}</dd></div><div><dt>Canlı PageRank hesabı</dt><dd>d = 0,80 · 10 iterasyon</dd></div></dl><div className="le-data-actions"><button type="button" className="primary-button" onClick={downloadGraph} disabled={!data.stats.pages}>{downloaded ? <Check size={16}/> : <Download size={16}/>}Sayfa ve bağlantıları indir</button><button type="button" className="secondary-button" onClick={() => onViewChange("index")}><Hash size={16}/>Kelime indeksini aç</button></div><p className="le-export-note">JSON dosyası sayfa başlıklarını, adresleri, bağlantı grafiğini ve PageRank puanlarını içerir. Kelime eşleşmelerini Kelime indeksi ekranında inceleyebilirsiniz.</p></section><PageCatalog key={runKey} snapshot={data} selectedUrl={selectedUrl} onPick={pickNode}/><div className="le-sample-callout"><div><h2>Colab verinizle çalışmak ister misiniz?</h2><p>Örnek veri ve JSON yükleme alanını açabilirsiniz.</p></div><button type="button" className="secondary-button" onClick={onOpenSample}>Örnek / Colab verisini aç<ArrowRight size={15}/></button></div></>}
    </>}
  </section>;
}
