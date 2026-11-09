
import { useId, useMemo, useState } from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import { computeRanks, getPageInfo, type Dataset } from "@/lib/search-engine";

type GraphProps = {
  dataset: Dataset;
  selectedUrl: string | null;
  onSelect: (url: string) => void;
  compact?: boolean;
  damping?: number;
  iterations?: number;
  ranks?: Record<string, number>;
};

type Point = { x: number; y: number; r: number; url: string; label: string };

const samplePositions: Record<string, [number, number, string]> = {
  "/": [105, 76, "Ana sayfa"],
  "/travel_guide.html": [295, 155, "Rehber"],
  "/ankara.html": [385, 64, "Ankara"],
  "/seymarecommends.html": [525, 100, "Şeyma"],
  "/oktayrecommends.html": [592, 235, "Oktay"],
  "/istanbul.html": [400, 273, "İstanbul"],
  "/galata_tower.html": [293, 355, "Galata"],
  "/maidens_tower.html": [530, 353, "Kız Kulesi"],
  "/konya.html": [154, 291, "Konya"],
  "/mevlana.html": [75, 197, "Mevlana"],
};

function clippedLabel(title: string) {
  return title.length > 19 ? `${title.slice(0, 17)}…` : title;
}

function edgePath(from: Point, to: Point, reciprocal: boolean) {
  if (from.url === to.url) {
    const x = from.x;
    const y = from.y - from.r;
    return `M ${x - 8} ${y + 2} C ${x - 46} ${y - 48}, ${x + 46} ${y - 48}, ${x + 8} ${y - 1}`;
  }
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.hypot(dx, dy) || 1;
  const bend = reciprocal ? 20 : 8;
  const cx = (from.x + to.x) / 2 - (dy / length) * bend;
  const cy = (from.y + to.y) / 2 + (dx / length) * bend;
  const fromLength = Math.hypot(cx - from.x, cy - from.y) || 1;
  const toLength = Math.hypot(to.x - cx, to.y - cy) || 1;
  const x1 = from.x + ((cx - from.x) / fromLength) * (from.r + 3);
  const y1 = from.y + ((cy - from.y) / fromLength) * (from.r + 3);
  const x2 = to.x - ((to.x - cx) / toLength) * (to.r + 7);
  const y2 = to.y - ((to.y - cy) / toLength) * (to.r + 7);
  return `M ${x1} ${y1} Q ${cx} ${cy}, ${x2} ${y2}`;
}

/** Uses the selected dataset's directed links; coordinates are presentation only. */
export function NetworkGraph({
  dataset,
  selectedUrl,
  onSelect,
  compact = false,
  damping = 0.8,
  iterations = 10,
  ranks: suppliedRanks,
}: GraphProps) {
  const markerPrefix = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const [zoom, setZoom] = useState(1);
  const [hoveredUrl, setHoveredUrl] = useState<string | null>(null);
  const ranks = useMemo(
    () => suppliedRanks ?? computeRanks(dataset.graph, damping, iterations),
    [suppliedRanks, dataset.graph, damping, iterations],
  );
  const highestRank = Math.max(...Object.values(ranks), 0);
  const allUrls = Object.keys(dataset.graph);
  const points = useMemo(() => {
    const urls = Object.keys(dataset.graph);
    const visible = urls.length > 30
      ? [...urls].sort((a, b) => (ranks[b] ?? 0) - (ranks[a] ?? 0)).slice(0, 30)
      : urls;
    // Keep a selected page visible even when the graph is limited to 30 nodes.
    if (selectedUrl && urls.includes(selectedUrl) && !visible.includes(selectedUrl)) {
      visible[visible.length - 1] = selectedUrl;
    }
    const maxRank = Math.max(...Object.values(ranks), 0.001);
    const result = new Map<string, Point>();
    const ranked = [...visible].sort((a, b) => (ranks[b] ?? 0) - (ranks[a] ?? 0));
    visible.forEach((url) => {
      const info = getPageInfo(url, dataset);
      const sample = dataset.origin === "sample" ? samplePositions[new URL(url).pathname] : undefined;
      const rankIndex = ranked.indexOf(url);
      let x = 350;
      let y = 202;
      let label = clippedLabel(info.title);
      if (sample) {
        [x, y, label] = sample;
      } else if (rankIndex > 0) {
        const innerCount = Math.min(9, ranked.length - 1);
        const outer = rankIndex > innerCount;
        const total = outer ? ranked.length - innerCount - 1 : innerCount;
        const index = outer ? rankIndex - innerCount - 1 : rankIndex - 1;
        const angle = (index / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2 + (outer ? 0.1 : 0);
        x += Math.cos(angle) * (outer ? 285 : 175);
        y += Math.sin(angle) * (outer ? 158 : 106);
      }
      result.set(url, {
        url,
        x,
        y,
        label,
        r: 10 + Math.sqrt(Math.max(ranks[url] ?? 0, 0) / maxRank) * 13,
      });
    });
    return result;
  }, [dataset, ranks, selectedUrl]);
  const edges = useMemo(() => {
    const visibleEdges: { from: Point; to: Point; reciprocal: boolean }[] = [];
    for (const [url, point] of points) {
      for (const target of new Set(dataset.graph[url] ?? [])) {
        const other = points.get(target);
        if (other) {
          visibleEdges.push({ from: point, to: other, reciprocal: (dataset.graph[target] ?? []).includes(url) });
        }
      }
    }
    return visibleEdges;
  }, [points, dataset.graph]);

  const activeUrl = hoveredUrl ?? selectedUrl;
  const activeVisible = activeUrl && points.has(activeUrl) ? activeUrl : null;
  const dense = edges.length > 120;
  // Paint highlighted edges last so dense background links cannot cover them.
  const orderedEdges = useMemo(() => activeVisible
    ? [...edges].sort((a, b) => Number(a.from.url === activeVisible || a.to.url === activeVisible) - Number(b.from.url === activeVisible || b.to.url === activeVisible))
    : edges, [edges, activeVisible]);
  const relatedUrls = new Set<string>();
  if (activeVisible) {
    relatedUrls.add(activeVisible);
    for (const edge of edges) {
      if (edge.from.url === activeVisible) relatedUrls.add(edge.to.url);
      if (edge.to.url === activeVisible) relatedUrls.add(edge.from.url);
    }
  }
  const effectiveZoom = compact ? 1 : zoom;
  const viewWidth = 700 / effectiveZoom;
  const viewHeight = 420 / effectiveZoom;
  const selectedPoint = selectedUrl ? points.get(selectedUrl) : undefined;
  const viewX = effectiveZoom > 1
    ? Math.max(0, Math.min(700 - viewWidth, (selectedPoint?.x ?? 350) - viewWidth / 2))
    : (700 - viewWidth) / 2;
  const viewY = effectiveZoom > 1
    ? Math.max(0, Math.min(420 - viewHeight, (selectedPoint?.y ?? 210) - viewHeight / 2))
    : (420 - viewHeight) / 2;
  const selectedExists = selectedUrl && Object.hasOwn(dataset.graph, selectedUrl);

  return (
    <div className={`iz-network${compact ? " iz-network--compact" : ""}`}>
      <style>{`
        .iz-network{position:relative;width:100%;font-family:inherit;min-width:0;color:#344e47}
        .iz-network__canvas{display:block;width:100%;height:auto;overflow:hidden;aspect-ratio:5/3;border-radius:12px;background-image:radial-gradient(#cbdad1 0.7px,transparent 0.7px);background-size:17px 17px;background-position:8px 8px}
        .iz-network--compact .iz-network__canvas{border-radius:0}
        .iz-network__node{cursor:pointer;outline:none}
        .iz-network__node .iz-network__focus{opacity:0;transition:opacity 140ms ease}
        .iz-network__node:focus-visible .iz-network__focus{opacity:1}
        .iz-network__node text{user-select:none}
        .iz-network__controls{position:absolute;top:10px;right:10px;z-index:1;display:flex;align-items:center;gap:2px;padding:4px;border:1px solid #dce5de;border-radius:9px;background:#ffffffed;box-shadow:0 2px 6px #214a3610}
        .iz-network__controls button{display:grid;place-items:center;width:30px;height:30px;border:0;background:transparent;border-radius:5px;color:#3c6257;cursor:pointer}
        .iz-network__controls button:hover{background:#eff5ef}
        .iz-network__controls button:disabled{opacity:.3;cursor:default}
        .iz-network__controls button:focus-visible{outline:2px solid #218371;outline-offset:2px}
        .iz-network__legend{display:flex;align-items:center;justify-content:center;gap:17px;flex-wrap:wrap;padding:12px 4px 3px;font-size:10px;line-height:1.5;color:#6a7c73}
        .iz-network__legend span{display:inline-flex;align-items:center;gap:6px}
        .iz-network__legend i{display:inline-block;width:15px;height:2px;border-radius:2px}
        .iz-network__note{margin:10px 0 0;font-size:11px;line-height:1.6;text-align:center;color:#6a7c73}
        @media(prefers-reduced-motion:reduce){.iz-network__node .iz-network__focus{transition:none}}
      `}</style>
      {!compact && (
        <div className="iz-network__controls" aria-label="Harita görünümü">
          <button type="button" aria-label="Uzaklaştır" title="Uzaklaştır" disabled={zoom <= 0.8} onClick={() => setZoom((value) => Math.max(0.8, +(value - 0.2).toFixed(1)))}><Minus size={15} /></button>
          <button type="button" aria-label="Görünümü sıfırla" title="Görünümü sıfırla" onClick={() => setZoom(1)}><RotateCcw size={14} /></button>
          <button type="button" aria-label="Yakınlaştır" title="Yakınlaştır" disabled={zoom >= 1.6} onClick={() => setZoom((value) => Math.min(1.6, +(value + 0.2).toFixed(1)))}><Plus size={15} /></button>
        </div>
      )}
      <svg
        className="iz-network__canvas"
        viewBox={`${viewX} ${viewY} ${viewWidth} ${viewHeight}`}
        role="group"
        aria-label={`Bağlantı haritası: ${allUrls.length} sayfadan ${points.size} sayfa gösteriliyor. Ayrıntılarını görmek için bir sayfa seçin.`}
      >
        <defs>
          {[['neutral', '#bdcfc3'], ['outgoing', '#278774'], ['incoming', '#6b92a6']].map(([name, color]) => (
            <marker id={`${markerPrefix}-${name}`} key={name} markerWidth="5" markerHeight="5" refX="4.2" refY="2.5" orient="auto" markerUnits="strokeWidth">
              <path d="M 0 0 L 5 2.5 L 0 5 z" fill={color} />
            </marker>
          ))}
        </defs>
        <g fill="none" aria-hidden="true">
          {orderedEdges.map(({ from, to, reciprocal }) => {
            const outgoing = from.url === activeVisible;
            const incoming = to.url === activeVisible;
            const kind = outgoing ? 'outgoing' : incoming ? 'incoming' : 'neutral';
            return <path key={`${from.url}→${to.url}`} d={edgePath(from, to, reciprocal)} stroke={outgoing ? '#278774' : incoming ? '#6b92a6' : '#bdcfc3'} strokeWidth={outgoing || incoming ? 2.1 : dense ? 0.85 : 1.25} strokeOpacity={outgoing || incoming ? 0.95 : activeVisible ? (dense ? 0.09 : 0.35) : dense ? 0.25 : 0.9} markerEnd={`url(#${markerPrefix}-${kind})`} />;
          })}
        </g>
        {Array.from(points.values()).map((point) => {
          const selected = point.url === selectedUrl;
          const active = point.url === activeVisible;
          const largest = highestRank > 0 && ranks[point.url] === highestRank;
          const dimmed = !!activeVisible && !relatedUrls.has(point.url);
          const deep = selected || largest;
          const rank = (ranks[point.url] ?? 0).toFixed(4);
          return (
            <g
              key={point.url}
              className="iz-network__node"
              role="button"
              tabIndex={0}
              aria-label={`${getPageInfo(point.url, dataset).title}, PageRank ${rank}`}
              aria-pressed={selected}
              onClick={() => onSelect(point.url)}
              onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(point.url); } }}
              onMouseEnter={() => setHoveredUrl(point.url)}
              onMouseLeave={() => setHoveredUrl(null)}
              onBlur={() => setHoveredUrl(null)}
              opacity={dimmed ? 0.48 : 1}
            >
              <title>{`${getPageInfo(point.url, dataset).title}\nPageRank: ${rank}\n${point.url}`}</title>
              <circle className="iz-network__focus" cx={point.x} cy={point.y} r={point.r + 9} fill="none" stroke="#218371" strokeWidth="2" strokeDasharray="3 3" />
              {(active || largest) && <circle cx={point.x} cy={point.y} r={point.r + (active ? 8 : 6)} fill="#e0eee4" opacity="0.85" />}
              <circle cx={point.x} cy={point.y} r={point.r} fill={deep ? '#227a65' : '#d4e6da'} stroke={selected ? '#165945' : '#f8fbf8'} strokeWidth={selected ? 2 : 3} />
              <circle cx={point.x} cy={point.y} r={deep ? 4 : 3} fill={deep ? '#e4f2e8' : '#7baf96'} />
              <text x={point.x} y={point.y + point.r + 19} textAnchor="middle" fill={deep ? '#254b3b' : '#61766a'} fontSize={compact ? 25 : points.size > 18 && !active ? 13 : 16} fontWeight={deep ? 650 : 500} stroke="#f8fbf8" strokeWidth="4" paintOrder="stroke" strokeLinejoin="round">{point.label}</text>
            </g>
          );
        })}
      </svg>
      <div className="iz-network__legend" aria-hidden="true">
        {selectedExists ? <><span><i style={{ background: '#278774' }} />Giden bağlantı</span><span><i style={{ background: '#6b92a6' }} />Gelen bağlantı</span></> : <span><i style={{ background: '#bdcfc3' }} />Oklar, bağlantının yönünü gösterir</span>}
        {!compact && <span>Daire boyutu: PageRank puanı</span>}
      </div>
      {allUrls.length > 30 && <p className="iz-network__note">{allUrls.length} sayfadan en yüksek puanlı olanlar ve varsa seçili sayfa gösteriliyor. Görünüm 30 sayfayla sınırlıdır.</p>}
    </div>
  );
}
