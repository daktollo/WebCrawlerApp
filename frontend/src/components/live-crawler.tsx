
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  Activity, AlertCircle, ArrowRight, ArrowUpRight, CheckCircle2, Clock3,
  Database, ExternalLink, FileText, Globe2, Hash, Info, LoaderCircle,
  Pause, Play, RefreshCw, RotateCcw, Search, SearchX, Settings2,
} from "lucide-react";
import {
  BOGAZICI_SEED, DEFAULT_PAGE_LIMIT, DEFAULT_SEED, MIN_PAGE_LIMIT, OFFICIAL_SEED, REQUESTED_SEED,
  type CrawlAction, type CrawlPhase, type CrawlStatus,
  type LiveSearchResponse, type LiveSearchResult,
} from "@/lib/crawler-types";

const PHASES: Record<CrawlPhase, { title: string; detail: string; tone: string }> = {
  idle: { title: "Başlamaya hazır", detail: "Tarama başlatıldığında bulunan sayfalar burada birikecek.", tone: "neutral" },
  running: { title: "Tarama sürüyor", detail: "Yeni sayfalar eklenirken mevcut indekste arayabilirsiniz.", tone: "active" },
  paused: { title: "Tarama duraklatıldı", detail: "Kuyruk saklandı. İndekslenen sayfalarda arama devam ediyor.", tone: "neutral" },
  completed: { title: "Tarama tamamlandı", detail: "Bu taramada keşfedilen uygun adresler işlendi.", tone: "success" },
  blocked: { title: "Kaynak erişimi engellendi", detail: "Kaynak siteye erişim sağlanamadığı için tarama durdu.", tone: "warning" },
  error: { title: "Kaynağa ulaşılamadı", detail: "Tarama durdu. Varsa daha önce indekslenen sayfalar aranabilir.", tone: "warning" },
  limit_reached: { title: "Sayfa sınırına ulaşıldı", detail: "Belirlenen kapsam tamamlandı. İndeks aramaya açık.", tone: "success" },
};

function shortUrl(value: string) {
  return value.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

function formatDate(value: string | null) {
  if (!value) return "Henüz yok";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("tr-TR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function number(value: number | undefined) {
  return value === undefined ? "—" : value.toLocaleString("tr-TR");
}

function parsePageLimit(value: string): number | null {
  if (!/^\d+$/.test(value)) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= MIN_PAGE_LIMIT ? parsed : null;
}

function safeLink(value: string) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : "#";
  } catch { return "#"; }
}

async function readApi<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store", credentials: "same-origin" });
  let body: unknown;
  try { body = await response.json(); } catch {
    throw new Error("Sunucudan beklenen yanıt alınamadı. Biraz sonra yeniden deneyin.");
  }
  if (!response.ok || !body || typeof body !== "object" || !("ok" in body) || !body.ok) {
    const message = body && typeof body === "object" && "error" in body && typeof body.error === "string"
      ? body.error : "İstek tamamlanamadı. Biraz sonra yeniden deneyin.";
    throw new Error(message);
  }
  return body as T;
}

function Result({ result, order, onShowNode }: { result: LiveSearchResult; order: number; onShowNode?: (url: string) => void }) {
  return <article className="lc-result">
    <span className="lc-result-order" aria-hidden="true">{String(order + 1).padStart(2, "0")}</span>
    <div className="lc-result-main">
      <div className="lc-result-source"><span className="lc-page-icon"><Globe2 size={17}/></span><div><span>İndekslenen web sayfası</span><span title={result.url}>{shortUrl(result.url)}</span></div></div>
      <a className="lc-result-title" href={safeLink(result.url)} target="_blank" rel="noopener noreferrer">{result.title || shortUrl(result.url)}<ArrowUpRight size={18}/></a>
      <p className="lc-result-description">{result.description || "Bu sayfa indekste yer alıyor; metin özeti bulunmuyor."}</p>
      <div className="lc-result-meta"><div className="lc-match-tags" aria-label="Eşleşme alanları">{result.matchSources.map(source => <span key={source}>{source === "content" ? "İçerik" : source === "title" ? "Başlık" : "Adres"} eşleşmesi</span>)}</div><span className="lc-result-date"><Clock3 size={12}/><time dateTime={result.indexedAt}>{formatDate(result.indexedAt)}</time></span></div>
      {onShowNode && <button type="button" className="text-button lc-map-link" onClick={() => onShowNode(result.url)}>Haritada gör<ArrowUpRight size={14}/></button>}
    </div>
    <div className="lc-rank"><span>PAGERANK</span><strong>{Number.isFinite(result.rank) ? result.rank.toLocaleString("tr-TR", { minimumFractionDigits: 6, maximumFractionDigits: 6 }) : "—"}</strong></div>
  </article>;
}

type ResetTarget = { seed: string; maxPages: number };

function ResetDialog({ target, busy, error, onCancel, onConfirm }: {
  target: ResetTarget; busy: boolean; error: string | null;
  onCancel: () => void; onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const element = dialog.current;
    element?.showModal();
    document.body.style.overflow = "hidden";
    cancelButton.current?.focus();
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, []);
  return <dialog ref={dialog} id="lc-reset-dialog" className="lc-reset-dialog" role="alertdialog" aria-labelledby="lc-reset-title" aria-describedby="lc-reset-description" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}>
    <span className="lc-reset-dialog-icon"><RotateCcw size={23}/></span>
    <h2 id="lc-reset-title">Tüm tarama verileri sıfırlansın mı?</h2>
    <p id="lc-reset-description">Sunucudaki tüm taramalara ait indekslenmiş sayfalar, kelime indeksi, bağlantı haritası, kuyruk ve hata kayıtları silinecek. <strong>Bu işlem geri alınamaz.</strong></p>
    <dl className="lc-reset-details"><div><dt>Yeni başlangıç adresi</dt><dd>{shortUrl(target.seed)}</dd></div><div><dt>Yeni taramanın sınırı</dt><dd>{number(target.maxPages)} adres</dd></div></dl>
    <p className="lc-reset-explanation">Tarama bu adresten yeniden başlayacak. İlk sayfalar indekslenene kadar arama sonuçları boş olacak.</p>
    {error && <p className="lc-control-error" role="alert">{error}</p>}
    <div className="lc-reset-dialog-actions"><button ref={cancelButton} type="button" className="secondary-button" disabled={busy} onClick={onCancel}>Vazgeç</button><button type="button" className="lc-reset-confirm" disabled={busy} onClick={onConfirm}>{busy ? <LoaderCircle className="lc-spin" size={16}/> : <RotateCcw size={16}/>} {busy ? "Sıfırlanıyor…" : "Sıfırla ve başlat"}</button></div>
  </dialog>;
}

type LiveCrawlerProps = {
  isVisible?: boolean;
  onStatusChange?: (status: CrawlStatus) => void;
  searchRequest?: { query: string; nonce: number } | null;
  onShowNode?: (url: string) => void;
  settingsRequest?: number;
};

export function LiveCrawler({ isVisible = true, onStatusChange, searchRequest, onShowNode, settingsRequest }: LiveCrawlerProps = {}) {
  const [status, setStatus] = useState<CrawlStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [draft, setDraft] = useState("Boğaziçi");
  const [query, setQuery] = useState("Boğaziçi");
  const [search, setSearch] = useState<LiveSearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(true);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [searchRefreshTick, setSearchRefreshTick] = useState(0);
  const [seed, setSeed] = useState(DEFAULT_SEED);
  const [maxPagesDraft, setMaxPagesDraft] = useState(String(DEFAULT_PAGE_LIMIT));
  const [controlBusy, setControlBusy] = useState<CrawlAction | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [controlMessage, setControlMessage] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<ResetTarget | null>(null);
  const seededControls = useRef(false);
  const mounted = useRef(false);
  const controlAbort = useRef<AbortController | null>(null);
  const controlInFlight = useRef(false);
  const searchAbort = useRef<AbortController | null>(null);
  const latestStatus = useRef<CrawlStatus | null>(null);
  const limitInput = useRef<HTMLInputElement | null>(null);
  const limitDirty = useRef(false);
  const limitEditing = useRef(false);
  const lastSettingsRequest = useRef<number | undefined>(undefined);

  const acceptStatus = useCallback((next: CrawlStatus) => {
    const previous = latestStatus.current;
    if (previous) {
      const previousTime = previous.updatedAt ? Date.parse(previous.updatedAt) : 0;
      const nextTime = next.updatedAt ? Date.parse(next.updatedAt) : 0;
      if (previousTime > nextTime || (previous.seed === next.seed && previous.revision > next.revision)) return previous;
    }
    if (previous?.seed !== next.seed || previous?.startedAt !== next.startedAt) {
      searchAbort.current?.abort();
      setSearch(null);
      setSearchError(null);
    }
    latestStatus.current = next;
    setStatus(next);
    if (!seededControls.current) {
      seededControls.current = true;
      setSeed(next.seed);
    }
    if (!limitDirty.current && !limitEditing.current) setMaxPagesDraft(String(next.maxPages));
    return next;
  }, []);

  const focusPageLimit = useCallback(() => {
    const input = limitInput.current;
    if (!input) return;
    input.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "center" });
    input.focus({ preventScroll: true });
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; controlAbort.current?.abort(); };
  }, []);

  useEffect(() => {
    if (status) onStatusChange?.(status);
  }, [status, onStatusChange]);

  const statusLoaded = status !== null;
  useEffect(() => {
    if (!settingsRequest || settingsRequest === lastSettingsRequest.current || !statusLoaded || controlBusy) return;
    const frame = requestAnimationFrame(() => {
      lastSettingsRequest.current = settingsRequest;
      focusPageLimit();
    });
    return () => cancelAnimationFrame(frame);
  }, [settingsRequest, statusLoaded, controlBusy, focusPageLimit]);

  useEffect(() => {
    if (!searchRequest) return;
    const word = searchRequest.query.trim().slice(0, 200);
    setDraft(word);
    setQuery(word);
    setRefreshVersion(version => version + 1);
  }, [searchRequest]);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let active: AbortController | undefined;
    async function poll() {
      active = new AbortController();
      const timeout = setTimeout(() => active?.abort(), 12000);
      try {
        const next = await readApi<CrawlStatus>("/api/crawl/status", { signal: active.signal });
        if (!stopped) { acceptStatus(next); setStatusError(null); }
      } catch (error) {
        if (!stopped) setStatusError(error instanceof Error && error.name !== "AbortError" ? error.message : "Tarama durumu şu anda alınamıyor. Yeniden bağlanılıyor.");
      } finally {
        clearTimeout(timeout);
        if (!stopped) timer = setTimeout(poll, 5000);
      }
    }
    void poll();
    return () => { stopped = true; if (timer) clearTimeout(timer); active?.abort(); };
  }, [acceptStatus, refreshVersion]);

  const activeSeed = status?.seed ?? DEFAULT_SEED;
  const activeStartedAt = status?.startedAt ?? null;
  const isBogaziciSource = activeSeed === BOGAZICI_SEED;

  useEffect(() => {
    if (!isVisible || status?.status !== "running") return;
    const timer = setInterval(() => setSearchRefreshTick(value => value + 1), 15000);
    return () => clearInterval(timer);
  }, [isVisible, status?.status]);

  useEffect(() => {
    if (!isVisible || !query.trim()) { setSearchLoading(false); setSearchError(null); return; }
    let stopped = false;
    const controller = new AbortController();
    searchAbort.current = controller;
    const sameRun = () => (latestStatus.current?.seed ?? DEFAULT_SEED) === activeSeed && (latestStatus.current?.startedAt ?? null) === activeStartedAt;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setSearchLoading(true);
    setSearchError(null);
    void readApi<LiveSearchResponse>(`/api/crawl/search?q=${encodeURIComponent(query)}&limit=30`, { signal: controller.signal })
      .then(next => { if (!stopped && sameRun() && next.startedAt === activeStartedAt) setSearch(next); })
      .catch(error => {
        if (!stopped && sameRun()) setSearchError(error instanceof Error && error.name !== "AbortError" ? error.message : "Arama yanıtı gecikti. Lütfen yeniden deneyin.");
      })
      .finally(() => { clearTimeout(timeout); if (!stopped && sameRun()) setSearchLoading(false); });
    return () => { stopped = true; clearTimeout(timeout); controller.abort(); if (searchAbort.current === controller) searchAbort.current = null; };
  }, [query, activeSeed, activeStartedAt, refreshVersion, searchRefreshTick, isVisible, status?.status]);

  function submitSearch(event?: FormEvent, word = draft) {
    event?.preventDefault();
    const clean = word.trim().slice(0, 200);
    setDraft(clean);
    setQuery(clean);
    if (clean === query) setRefreshVersion(version => version + 1);
  }

  function requestReset() {
    if (controlInFlight.current) return;
    const maxPages = parsePageLimit(maxPagesDraft);
    if (maxPages === null) { focusPageLimit(); return; }
    setControlError(null);
    setResetTarget({ seed, maxPages });
  }

  async function control(action: CrawlAction, resetSelection?: ResetTarget) {
    if (controlInFlight.current) return;
    if (action === "reset" && !resetSelection) return;
    const requestedLimit = resetSelection?.maxPages ?? parsePageLimit(maxPagesDraft);
    const requestedSeed = resetSelection?.seed ?? seed;
    if (action !== "pause" && requestedLimit === null) {
      focusPageLimit();
      return;
    }
    if (action === "set_limit" && (!status || status.status === "idle" || seed !== status.seed)) return;
    controlInFlight.current = true;
    setControlBusy(action);
    setControlError(null);
    setControlMessage(null);
    const controller = new AbortController();
    controlAbort.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const next = await readApi<CrawlStatus>("/api/crawl/control", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ action, ...(action === "pause" ? {} : { maxPages: requestedLimit }), ...(["start", "set_limit", "reset"].includes(action) ? { seed: requestedSeed } : {}), ...(action === "reset" ? { confirmReset: true } : {}) }),
      });
      if (!mounted.current) return;
      const accepted = acceptStatus(next);
      setSeed(accepted.seed);
      if (action !== "pause") {
        limitDirty.current = false;
        setMaxPagesDraft(String(accepted.maxPages));
      }
      if (action === "reset") {
        searchAbort.current?.abort();
        setSearch(null);
        setSearchError(null);
        setResetTarget(null);
      }
      setStatusError(null);
      setControlMessage(action === "set_limit" ? `Sayfa sınırı ${number(accepted.maxPages)} adres olarak kaydedildi.`
        : action === "reset" ? "Tarama verileri sıfırlandı. Seçili başlangıç adresinden yeniden tarama başlıyor."
          : action === "pause" ? "Tarama duraklatıldı. Mevcut indeks aramaya açık." : "Tarama isteği alındı. İlerleme otomatik güncellenecek.");
      setRefreshVersion(version => version + 1);
    } catch (error) {
      if (mounted.current) {
        if (action === "reset" && controller.signal.aborted) {
          // A timed-out response does not prove the reset failed. Require a
          // fresh confirmation before another destructive request is possible.
          setResetTarget(null);
          setControlError("Sıfırlama isteğinin sonucu doğrulanamadı. Güncel durum yenileniyor; tekrar sıfırlamadan önce tarama bilgilerini kontrol edin.");
          setRefreshVersion(version => version + 1);
        } else setControlError(error instanceof Error && error.name !== "AbortError" ? error.message : "İsteğin sonucu alınamadı. Güncel durumu kontrol edip yeniden deneyin.");
      }
    } finally {
      clearTimeout(timeout);
      controlInFlight.current = false;
      if (mounted.current) setControlBusy(null);
    }
  }

  const phase = status ? PHASES[status.status] : null;
  const running = status?.status === "running";
  const sourceUnavailable = status?.status === "error" || status?.status === "blocked";
  const indexedPages = status?.indexedPages ?? search?.indexedPages;
  const results = query ? search?.results ?? [] : [];
  const hasPreviousQuery = Boolean(query && search && search.query !== query);
  const initialLoading = query && searchLoading && !search;
  const seedChanged = Boolean(status && seed !== status.seed);
  const maxPages = parsePageLimit(maxPagesDraft);
  const limitValid = maxPages !== null;
  const limitChanged = Boolean(status && limitValid && maxPages !== status.maxPages);
  const limitMustIncrease = Boolean(status?.status === "limit_reached" && !seedChanged && maxPages !== null && maxPages <= status.visitedPages);
  const mainAction: CrawlAction = seedChanged || !status || status.status === "idle" || status.status === "completed" ? "start"
    : status.status === "paused" || status.status === "limit_reached" ? "resume" : "retry";
  const mainActionText = mainAction === "start" ? (seedChanged ? "Seçili adresten başlat" : status?.status === "completed" ? "Yeniden tara" : "Taramayı başlat")
    : mainAction === "resume" ? (limitChanged ? "Yeni sınırla devam et" : "Taramaya devam et") : "Yeniden dene";

  return <section className="lc-root" aria-labelledby="lc-title">
    <header className="lc-hero">
      <span className="lc-eyebrow"><span/>KALICI WEB İNDEKSİ</span>
      <h1 id="lc-title">Web indeksinde <span>arayın.</span></h1>
      <p>Tarama sürerken arama devam eder. Her yeni sayfa, indekse kaydedildiğinde sonuçlara katılır.</p>
      <form className="lc-search-form" onSubmit={submitSearch} role="search">
        <Search size={23} aria-hidden="true"/>
        <input id="live-crawl-query" aria-label="Web indeksinde aranacak kelimeler" placeholder="Bir kelime veya konu yazın..." value={draft} onChange={event => setDraft(event.target.value)} autoComplete="off" maxLength={200}/>
        <button className="primary-button" type="submit">Ara<ArrowRight size={17}/></button>
      </form>
      <div className="lc-search-hints"><div><span>Bir sorgu deneyin:</span>{["Boğaziçi", "araştırma", "kampüs"].map(word => <button key={word} type="button" onClick={() => submitSearch(undefined, word)}><Hash size={12}/>{word}</button>)}</div><span><Database size={12}/>İndekslenen içerikte arama</span></div>
    </header>

    <div className={`lc-crawl-banner lc-tone-${phase?.tone ?? "neutral"}`}>
      <span className={`lc-activity-icon ${running ? "lc-active" : ""}`}>{sourceUnavailable ? <AlertCircle size={21}/> : status?.status === "completed" || status?.status === "limit_reached" ? <CheckCircle2 size={21}/> : <Activity size={21}/>}</span>
      <div className="lc-crawl-summary"><div><h2>{phase?.title ?? (statusError ? "Tarama durumu alınamıyor" : "Tarama durumu yükleniyor")}</h2>{running && <span className="lc-live-label"><span/>AKTİF</span>}</div><p>{phase?.detail ?? "İndeks ve kuyruk bilgileri kontrol ediliyor."}</p></div>
      <div className="lc-banner-source"><span>BAŞLANGIÇ ADRESİ</span><a href={safeLink(activeSeed)} target="_blank" rel="noopener noreferrer">{shortUrl(activeSeed)}<ArrowUpRight size={13}/></a></div>
    </div>
    {statusError && <div className="lc-inline-alert" role="status"><Info size={16}/><p>{statusError}{status ? " Son alınan durum gösteriliyor." : ""}</p><button onClick={() => setRefreshVersion(value => value + 1)} className="text-button">Yenile<RefreshCw size={13}/></button></div>}

    <div className="lc-stats" aria-label="Canlı indeks özeti">
      <div><span className="lc-stat-icon"><FileText size={19}/></span><div><strong>{number(indexedPages)}</strong><span>indekslenen sayfa</span></div></div>
      <div><span className="lc-stat-icon"><Clock3 size={19}/></span><div><strong>{number(status?.queuedPages)}</strong><span>kuyruktaki adres</span></div></div>
      <div><span className="lc-stat-icon"><Hash size={20}/></span><div><strong>{number(status?.indexedWords)}</strong><span>indekslenen kelime</span></div></div>
      <div><span className="lc-stat-icon"><AlertCircle size={19}/></span><div><strong>{number(status?.failedPages)}</strong><span>erişim hatası</span></div></div>
    </div>
    {status && <div className="lc-settings-bar"><span>{status.status === "idle" ? "Başlangıç sınırı" : "Kayıtlı sınır"}: <strong>{number(status.maxPages)} adres</strong></span><button type="button" className="text-button" aria-controls="lc-max-pages" disabled={Boolean(controlBusy)} onClick={focusPageLimit}><Settings2 size={14}/>Sayfa sınırını değiştir<ArrowRight size={13}/></button></div>}

    <div className="lc-workspace">
      <section className="lc-results" aria-labelledby="lc-results-title">
        <div className="lc-results-heading"><h2 id="lc-results-title">Arama sonuçları{search && query && <span>{number(search.total)}</span>}</h2><span>{searchLoading ? <><LoaderCircle size={13} className="lc-spin"/>Güncelleniyor</> : <><Database size={13}/>PageRank sırası</>}</span></div>
        <div className="lc-results-caption" aria-live="polite">{!query ? "Aramak istediğiniz kelimeleri yukarıya yazın." : initialLoading ? "İndekste aranıyor…" : search ? <><strong>“{search.query}”</strong> için <strong>{number(search.total)} sonuç</strong><span> · {number(search.indexedPages)} sayfa içinde</span></> : searchError ? "Arama yanıtı alınamadı." : "İndeks yanıtı bekleniyor."}</div>
        {searchError && <div className="lc-inline-alert lc-search-error" role="alert"><AlertCircle size={16}/><p>{searchError}{search ? " Son başarılı aramanın sonuçları korunuyor." : ""}</p><button className="text-button" onClick={() => setRefreshVersion(value => value + 1)}>Tekrar dene</button></div>}
        {hasPreviousQuery && <p className="lc-stale-query" role="status">{searchLoading ? `“${query}” aranıyor; bu sırada önceki sorgunun sonuçları gösteriliyor.` : `“${query}” için yeni yanıt alınamadı. Aşağıda “${search?.query}” sorgusunun sonuçları var.`}</p>}
        <div className="lc-result-list" aria-busy={searchLoading}>
          {initialLoading ? <div className="lc-loading" role="status"><LoaderCircle className="lc-spin" size={27}/><strong>İndekse bağlanılıyor</strong><span>Sonuçlar hazır olduğunda burada görünecek.</span></div>
          : results.length ? results.map((result, index) => <Result key={result.url} result={result} order={index} onShowNode={onShowNode}/>)
          : <div className="lc-empty"><span className="lc-empty-icon">{!query ? <Search size={29}/> : searchError && !search ? <AlertCircle size={29}/> : indexedPages === 0 ? <Database size={29}/> : <SearchX size={29}/>}</span>
            <h3>{!query ? "Neyi keşfetmek istersiniz?" : searchError && !search ? "Arama servisine ulaşılamıyor." : indexedPages === 0 ? "Henüz indekslenen sayfa yok." : "Bu sorguyla eşleşen sayfa yok."}</h3>
            <p>{!query ? "Bir veya birkaç kelime girin. Arama, o ana kadar indekslenen sayfalarda yapılır."
              : searchError && !search ? "İndeksin boş olduğu sonucuna varamayız. Bağlantı yeniden kurulduğunda arama sonuçları güncellenecek."
              : indexedPages === 0 ? (sourceUnavailable ? "Tarama kaynağına erişilemedi. Erişim ayrıntısını tarama panelinde görebilirsiniz. İlk sayfa başarıyla indekslendiğinde arama kullanılabilir olacak." : running ? "Crawler başlangıç adresini işliyor. İlk sayfa kaydedildiğinde sonuçlar otomatik güncellenecek." : "Tarama başlatıldığında erişilebilen sayfalar bu indekse eklenecek.")
              : running ? "Şu ana kadar indekslenen sayfalarda eşleşme bulunamadı. Tarama sürdükçe sonuçlar otomatik güncellenir." : "Farklı veya daha kısa bir sorgu deneyin. Arama yalnızca indekslenen sayfaları kapsar."}</p>
            {query && indexedPages !== 0 && !searchError && <button className="secondary-button" onClick={() => { setDraft(""); setQuery(""); document.getElementById("live-crawl-query")?.focus(); }}>Yeni bir arama yap<Search size={15}/></button>}
          </div>}
        </div>
        {query && search && search.total > search.results.length && <p className="lc-result-limit">İlk {search.results.length} sonuç gösteriliyor. Daha belirli kelimelerle aramanızı daraltabilirsiniz.</p>}
        <p className="lc-search-footnote"><Info size={14}/><span>Sorgudaki kelimelerin tümünü içeren sayfalar gösterilir. Eşleşmeler içerik, başlık ve adres bilgisine göre bulunur; sayfalar PageRank ile sıralanır.</span></p>
      </section>

      <aside className="lc-side" aria-label="Tarama ayrıntıları">
        <section className="lc-panel lc-progress-panel"><div className="lc-panel-heading"><h2><Activity size={17}/>Tarama akışı</h2><span className={`lc-phase-tag lc-tone-${phase?.tone ?? "neutral"}`}>{phase?.title ?? "Yükleniyor"}</span></div>
          <div className="lc-capacity"><span>İşlenen adres / sınır</span><strong>{number(status?.visitedPages)} / {number(status?.maxPages)}</strong></div>
          <div className="lc-progress-track" role="progressbar" aria-label="İşlenen adres sayısı" aria-valuemin={0} aria-valuemax={status?.maxPages ?? DEFAULT_PAGE_LIMIT} aria-valuenow={Math.min(status?.visitedPages ?? 0, status?.maxPages ?? DEFAULT_PAGE_LIMIT)} aria-valuetext={`${number(status?.visitedPages)} adres işlendi; sınır ${number(status?.maxPages)} adres.`}><span style={{ width: `${Math.min(100, ((status?.visitedPages ?? 0) / (status?.maxPages || DEFAULT_PAGE_LIMIT)) * 100)}%` }}/></div>
          <dl className="lc-progress-details"><div><dt>İşlenen adres</dt><dd>{number(status?.visitedPages)}</dd></div><div><dt>Atlanan adres</dt><dd>{number(status?.skippedPages)}</dd></div><div><dt>Son indeksleme</dt><dd>{formatDate(status?.lastIndexedAt ?? null)}</dd></div></dl>
          {running && status?.currentUrl && <div className="lc-current"><span><LoaderCircle className="lc-spin" size={12}/>Şimdi işleniyor</span><p title={status.currentUrl}>{shortUrl(status.currentUrl)}</p></div>}
          {status?.lastError && <div className="lc-source-error" role="status"><AlertCircle size={16}/><div><strong>Son erişim bildirimi</strong><p>{status.lastError}</p></div></div>}
          <p className="lc-runtime-note"><Clock3 size={14}/><span>Tarama sunucu çalıştığı sürece arka planda ilerler. Sunucu kapanınca kuyruk saklanır; yeniden açıldığında devam eder.</span></p>
        </section>

        {status && <section className="lc-panel lc-controls" id="lc-crawl-settings"><div className="lc-panel-heading"><h2><Settings2 size={17}/>Tarama yönetimi</h2></div>
          <label htmlFor="lc-seed">Başlangıç adresi</label><select id="lc-seed" value={seed} onChange={event => { setSeed(event.target.value); setControlMessage(null); }} disabled={running || Boolean(controlBusy)}><option value={BOGAZICI_SEED}>www.bogazici.edu.tr · Boğaziçi Üniversitesi</option><option value={REQUESTED_SEED}>www.tsk.gov.tr · Önceki kaynak</option><option value={OFFICIAL_SEED}>www.tsk.tr · Genelkurmay Başkanlığı</option></select>
          {seed === BOGAZICI_SEED && seedChanged && <p className="lc-control-tip">www.bogazici.edu.tr, bogazici.edu.tr adresine yönlenir. Yeni tarama bu adresten başlayacak.</p>}
          <div className="lc-limit-heading"><label htmlFor="lc-max-pages">Sayfa sınırı</label><span>Üst sınır yok</span></div>
          <div className="lc-limit-edit"><input ref={limitInput} id="lc-max-pages" type="number" min={MIN_PAGE_LIMIT} step={1} inputMode="numeric" value={maxPagesDraft} disabled={Boolean(controlBusy)} aria-invalid={!limitValid} aria-describedby={`lc-limit-help lc-limit-status${!limitValid ? " lc-limit-error" : ""}`}
            onFocus={() => { limitEditing.current = true; }}
            onBlur={() => {
              limitEditing.current = false;
              const saved = latestStatus.current?.maxPages ?? DEFAULT_PAGE_LIMIT;
              if (!limitDirty.current || parsePageLimit(maxPagesDraft) === saved) {
                limitDirty.current = false;
                setMaxPagesDraft(String(saved));
              }
            }}
            onChange={event => {
              const value = event.target.value;
              limitDirty.current = value !== String(latestStatus.current?.maxPages ?? DEFAULT_PAGE_LIMIT);
              setMaxPagesDraft(value);
              setControlMessage(null);
              setControlError(null);
            }}/><button type="button" className="secondary-button lc-limit-save" disabled={!limitValid || !limitChanged || Boolean(controlBusy) || seedChanged || status.status === "idle"} onClick={() => void control("set_limit")}>{controlBusy === "set_limit" && <LoaderCircle className="lc-spin" size={14}/>}Sınırı kaydet</button></div>
          {!limitValid && <p id="lc-limit-error" className="lc-limit-error" role="alert"><AlertCircle size={13}/>{Number(maxPagesDraft) > Number.MAX_SAFE_INTEGER ? "Girilen sayı çok büyük. Daha küçük bir tam sayı girin." : `${MIN_PAGE_LIMIT} veya daha büyük bir tam sayı girin.`}</p>}
          <div className="lc-limit-summary" id="lc-limit-status"><span>Kayıtlı sınır <strong>{status.status === "idle" ? "Henüz yok" : number(status.maxPages)}</strong></span><span>İşlenen adres <strong>{number(status.visitedPages)}</strong></span></div>
          <p id="lc-limit-help" className="lc-control-tip">Sınır, tüm sitelerde işlenen adreslerin toplamıdır. Atlanan ve hata alınan adresler de sayılır. Sınırı azaltmak mevcut indeksi silmez.</p>
          {(seedChanged || status.status === "idle") ? <p className="lc-control-tip">Girdiğiniz sınır yeni taramayı başlattığınızda uygulanır.</p> : limitChanged && <p className="lc-limit-pending">Değişiklik henüz kaydedilmedi.{!running && ` “${mainActionText}” düğmesi de bu sınırı uygular.`}</p>}
          <div className="lc-control-actions">{running ? <button type="button" className="secondary-button" disabled={Boolean(controlBusy)} onClick={() => void control("pause")}>{controlBusy === "pause" ? <LoaderCircle className="lc-spin" size={15}/> : <Pause size={15}/>}Duraklat</button> : <button type="button" className="primary-button" disabled={Boolean(controlBusy) || !limitValid || limitMustIncrease} onClick={() => void control(mainAction)}>{controlBusy && controlBusy !== "set_limit" ? <LoaderCircle className="lc-spin" size={15}/> : mainAction === "retry" ? <RefreshCw size={15}/> : <Play size={15}/>} {mainActionText}</button>}</div>
          {limitMustIncrease && <p className="lc-control-tip">Devam etmek için sınırı işlenen adres sayısının ({number(status.visitedPages)}) üzerine çıkarın.</p>}
          {status.status === "limit_reached" && !seedChanged && limitValid && !limitMustIncrease && <p className="lc-control-tip">Tarama bekliyor. Devam et düğmesiyle kalan kuyruğu işleyebilirsiniz.</p>}
          <div className="lc-reset-section"><button type="button" className="lc-reset-button" aria-haspopup="dialog" aria-controls="lc-reset-dialog" disabled={Boolean(controlBusy) || !limitValid} onClick={requestReset}><RotateCcw size={15}/>Taramayı sıfırla ve yeniden başlat</button><p>Mevcut arama verilerini ve kuyruğu temizler. Devam etmeden önce onayınız alınır.</p></div>
          {controlError && !resetTarget && <p className="lc-control-error" role="alert">{controlError}</p>}{controlMessage && <p className="lc-control-success" role="status">{controlMessage}</p>}
        </section>}

        <section className="lc-panel lc-source-note"><div className="lc-panel-heading"><h2><Globe2 size={17}/>Başlangıç ve kapsam</h2></div><p>Başlangıç adresi: <strong>{shortUrl(activeSeed)}</strong>.</p><p><strong>Bağlantılarla keşfedilen siteler</strong> taranır. Alt alan adları ve başka sitelerdeki sayfalar da aynı arama indeksine katılabilir.</p>{isBogaziciSource && <p className="lc-source-small">www.bogazici.edu.tr, bogazici.edu.tr adresine yönlenir. Bu adres taramanın başlangıç noktasıdır.</p>}<a href={safeLink(activeSeed)} target="_blank" rel="noopener noreferrer">{isBogaziciSource ? "Boğaziçi Üniversitesi sitesini aç" : "Başlangıç sitesini aç"}<ExternalLink size={12}/></a><p className="lc-source-small">Her sitenin robots.txt kuralları kontrol edilir. Erişim ve doğrulama engelleri tarama panelinde gösterilir.</p></section>

        <section className="lc-panel lc-recent"><div className="lc-panel-heading"><h2><FileText size={17}/>Son eklenen sayfalar</h2></div>{status?.recentPages.length ? <ul>{status.recentPages.slice(0, 5).map(page => <li key={page.url}><a href={safeLink(page.url)} target="_blank" rel="noopener noreferrer"><span>{page.title || shortUrl(page.url)}</span><ArrowUpRight size={13}/></a><time dateTime={page.indexedAt}>{formatDate(page.indexedAt)}</time></li>)}</ul> : <p className="lc-recent-empty">Başarıyla indekslenen sayfalar burada listelenecek.</p>}</section>
        {Boolean(status?.recentErrors.length) && <details className="lc-errors"><summary>Son erişim hataları <span>{status?.recentErrors.length}</span></summary><ul>{status?.recentErrors.slice(0, 5).map((error, i) => <li key={`${error.url}-${i}`}><strong>{shortUrl(error.url)}</strong><p>{error.error}</p></li>)}</ul></details>}
      </aside>
    </div>
    {resetTarget && <ResetDialog target={resetTarget} busy={controlBusy === "reset"} error={controlError} onCancel={() => { if (!controlInFlight.current) { setResetTarget(null); setControlError(null); } }} onConfirm={() => void control("reset", resetTarget)}/>}
  </section>;
}
