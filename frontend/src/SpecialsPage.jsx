import { useState, useEffect, useCallback, useRef } from "react";

const SUPABASE_URL = "https://bqwexelzzxgolvzmmovo.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxd2V4ZWx6enhnb2x2em1tb3ZvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxNjkwNDEsImV4cCI6MjA4ODc0NTA0MX0.GZFS5ifuNOD6f3xpHMhIB0F7XURlve-cdV3T9BXIOj4";

const PAGE_SIZE = 40;

const STORE_CONFIG = {
  woolworths: { label: "Woolworths", color: "#00c6ff", bg: "rgba(0,198,255,0.12)", border: "rgba(0,198,255,0.25)", logo: "🟢" },
  coles:      { label: "Coles",      color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.25)", logo: "🔴" },
};

const SORT_OPTIONS = [
  { value: "saving_pct.desc", label: "Best % Off" },
  { value: "saving.desc",     label: "Most $ Saved" },
  { value: "price.asc",       label: "Lowest Price" },
  { value: "price.desc",      label: "Highest Price" },
];

async function fetchSpecials({ store, halfPrice, search, sort, page }) {
  const [col, dir] = sort.split(".");
  let url = `${SUPABASE_URL}/rest/v1/specials?select=*&order=${col}.${dir}.nullslast&limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`;

  if (store !== "all") url += `&store=eq.${store}`;
  if (halfPrice) url += `&is_half_price=eq.true`;
  if (search) {
    // Normalise: strip hyphens, build full-text search query
    const normalised = search.replace(/-/g, ' ').trim();
    const ftsQuery = normalised.split(/\s+/).filter(Boolean).join(' & ');
    url += `&name_search=fts.${encodeURIComponent(ftsQuery)}`;
  }

  const res = await fetch(url, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "count=exact",
    },
  });
  const total = parseInt(res.headers.get("content-range")?.split("/")[1] || "0");
  const data = await res.json();
  return { data, total };
}

export default function SpecialsPage({ onAddToList }) {
  const [store, setStore]         = useState("all");
  const [halfPrice, setHalfPrice] = useState(false);
  const [sort, setSort]           = useState("saving_pct.desc");
  const [search, setSearch]       = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage]           = useState(0);
  const [specials, setSpecials]   = useState([]);
  const [total, setTotal]         = useState(0);
  const [loading, setLoading]     = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const debounceRef = useRef();

  // Debounce search
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0);
    }, 380);
  }, [search]);

  // Reset page on filter change
  useEffect(() => { setPage(0); setSpecials([]); }, [store, halfPrice, sort, debouncedSearch]);

  // Fetch
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (page === 0) setLoading(true);
      else setLoadingMore(true);
      try {
        const { data, total } = await fetchSpecials({ store, halfPrice, search: debouncedSearch, sort, page });
        if (!cancelled) {
          setSpecials(prev => page === 0 ? data : [...prev, ...data]);
          setTotal(total);
        }
      } finally {
        if (!cancelled) { setLoading(false); setLoadingMore(false); }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [store, halfPrice, sort, debouncedSearch, page]);

  const hasMore = specials.length < total;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
      <style>{`
        .sp-chip { border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.45); font-family: 'DM Sans', sans-serif; }
        .sp-chip.active-ww { background: rgba(0,198,255,0.15); border-color: rgba(0,198,255,0.4); color: #00c6ff; }
        .sp-chip.active-co { background: rgba(248,113,113,0.15); border-color: rgba(248,113,113,0.4); color: #f87171; }
        .sp-chip.active-all { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.25); color: #fff; }
        .sp-chip.active-hp { background: rgba(251,191,36,0.15); border-color: rgba(251,191,36,0.35); color: #fbbf24; }
        .sp-card { background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; overflow: hidden; transition: all 0.18s; cursor: default; }
        .sp-card:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.13); transform: translateY(-1px); }
        .sp-add-btn { background: rgba(0,198,255,0.12); border: 1px solid rgba(0,198,255,0.25); border-radius: 8px; color: #00c6ff; font-size: 11px; font-weight: 700; padding: 5px 10px; cursor: pointer; font-family: 'DM Sans', sans-serif; transition: all 0.15s; white-space: nowrap; }
        .sp-add-btn:hover { background: rgba(0,198,255,0.22); border-color: rgba(0,198,255,0.5); }
        .sp-search { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #fff; font-size: 14px; padding: 10px 14px 10px 38px; font-family: 'DM Sans', sans-serif; width: 100%; transition: border-color 0.15s; }
        .sp-search:focus { border-color: rgba(0,198,255,0.4); background: rgba(0,198,255,0.05); }
        .sp-search::placeholder { color: rgba(255,255,255,0.25); }
        .sp-select { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: rgba(255,255,255,0.7); font-size: 12px; padding: 8px 10px; font-family: 'DM Sans', sans-serif; cursor: pointer; }
        .sp-select option { background: #0d1f3c; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .sp-card { animation: fadeUp 0.2s ease both; }
        .sp-skeleton { background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; border-radius: 14px; }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
      `}</style>

      {/* Header */}
      <div style={{ padding: "20px 16px 12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 14 }}>
          <div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 3 }}>This Week</div>
            <div style={{ color: "#fff", fontSize: 26, fontWeight: 800, fontFamily: "'Syne', sans-serif", lineHeight: 1 }}>Specials</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ color: "#00c6ff", fontSize: 20, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>{total.toLocaleString()}</div>
            <div style={{ color: "rgba(255,255,255,0.25)", fontSize: 10 }}>deals found</div>
          </div>
        </div>

        {/* Search */}
        <div style={{ position: "relative", marginBottom: 12 }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "rgba(255,255,255,0.25)", fontSize: 15, pointerEvents: "none" }}>🔍</span>
          <input
            className="sp-search"
            placeholder="Search specials... e.g. chicken, milk, chips"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button onClick={() => setSearch("")} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 16 }}>×</button>
          )}
        </div>

        {/* Filters row */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <button className={`sp-chip ${store === "all" ? "active-all" : ""}`} onClick={() => setStore("all")}>All Stores</button>
          <button className={`sp-chip ${store === "woolworths" ? "active-ww" : ""}`} onClick={() => setStore(store === "woolworths" ? "all" : "woolworths")}>🟢 Woolworths</button>
          <button className={`sp-chip ${store === "coles" ? "active-co" : ""}`} onClick={() => setStore(store === "coles" ? "all" : "coles")}>🔴 Coles</button>
          <button className={`sp-chip ${halfPrice ? "active-hp" : ""}`} onClick={() => setHalfPrice(h => !h)}>½ Half Price</button>
          <select className="sp-select" value={sort} onChange={e => setSort(e.target.value)} style={{ marginLeft: "auto" }}>
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Grid */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 24px" }}>
        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="sp-skeleton" style={{ height: 180, animationDelay: `${i * 0.05}s` }} />
            ))}
          </div>
        ) : specials.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.25)" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>No specials found</div>
            <div style={{ fontSize: 12, marginTop: 6 }}>Try a different search or filter</div>
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {specials.map((item, i) => (
                <SpecialCard
                  key={`${item.store}-${item.stockcode}`}
                  item={item}
                  idx={i}
                  onAdd={onAddToList}
                />
              ))}
            </div>

            {hasMore && (
              <div style={{ textAlign: "center", marginTop: 20 }}>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={loadingMore}
                  style={{ background: "rgba(0,198,255,0.1)", border: "1px solid rgba(0,198,255,0.25)", borderRadius: 10, color: "#00c6ff", fontSize: 13, fontWeight: 600, padding: "12px 32px", cursor: loadingMore ? "default" : "pointer", fontFamily: "'DM Sans', sans-serif", opacity: loadingMore ? 0.6 : 1 }}
                >
                  {loadingMore ? "Loading..." : `Load more · ${(total - specials.length).toLocaleString()} remaining`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function SpecialCard({ item, idx, onAdd }) {
  const cfg = STORE_CONFIG[item.store] || STORE_CONFIG.woolworths;
  const savingPct = item.saving_pct ? Math.round(item.saving_pct) : null;
  const imgUrl = item.thumbnail
    ? (item.store === "woolworths"
        ? `https://cdn0.woolworths.media/content/wowproductimages/small/${item.thumbnail}.jpg`
        : item.thumbnail)
    : null;

  return (
    <div className="sp-card" style={{ animationDelay: `${(idx % PAGE_SIZE) * 0.02}s`, display: "flex", flexDirection: "column" }}>
      {/* Image area */}
      <div style={{ position: "relative", background: "rgba(255,255,255,0.03)", aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
        {imgUrl ? (
          <img
            src={imgUrl}
            alt={item.name}
            style={{ width: "85%", height: "85%", objectFit: "contain" }}
            onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
          />
        ) : null}
        <div style={{ display: imgUrl ? "none" : "flex", alignItems: "center", justifyContent: "center", width: "100%", height: "100%", fontSize: 32 }}>🛒</div>

        {/* Store pill */}
        <div style={{ position: "absolute", top: 7, left: 7, background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 6, padding: "2px 7px", fontSize: 9, fontWeight: 700, color: cfg.color, letterSpacing: 0.5 }}>
          {cfg.label.toUpperCase()}
        </div>

        {/* Saving badge */}
        {savingPct && (
          <div style={{ position: "absolute", top: 7, right: 7, background: item.is_half_price ? "rgba(251,191,36,0.2)" : "rgba(74,222,128,0.15)", border: `1px solid ${item.is_half_price ? "rgba(251,191,36,0.4)" : "rgba(74,222,128,0.35)"}`, borderRadius: 6, padding: "2px 7px", fontSize: 10, fontWeight: 800, color: item.is_half_price ? "#fbbf24" : "#4ade80", fontFamily: "'DM Mono', monospace" }}>
            -{savingPct}%
          </div>
        )}
      </div>

      {/* Info area */}
      <div style={{ padding: "10px 10px 8px", flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        {/* Name */}
        <div style={{ fontSize: 11.5, fontWeight: 600, color: "rgba(255,255,255,0.82)", lineHeight: 1.35, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {item.name}
        </div>

        {/* Price row */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 5, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: "#fff", fontFamily: "'DM Mono', monospace" }}>${item.price?.toFixed(2)}</span>
          {item.was_price && (
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.28)", textDecoration: "line-through" }}>${item.was_price?.toFixed(2)}</span>
          )}
        </div>

        {/* Unit price */}
        {item.unit_price && (
          <div style={{ fontSize: 9.5, color: "rgba(255,255,255,0.25)" }}>{item.unit_price}</div>
        )}

        {/* Offer description (multi-buy) */}
        {item.offer_description && (
          <div style={{ fontSize: 10, fontWeight: 600, color: "#a78bfa", background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.2)", borderRadius: 5, padding: "2px 7px", alignSelf: "flex-start" }}>
            {item.offer_description}
          </div>
        )}

        {/* Saving */}
        {item.saving > 0 && (
          <div style={{ fontSize: 10, color: "#4ade80", fontWeight: 600 }}>Save ${item.saving?.toFixed(2)}</div>
        )}

        {/* Add to list btn */}
        {onAdd && (
          <button className="sp-add-btn" onClick={() => onAdd(item.name, item)} style={{ marginTop: "auto", alignSelf: "flex-start" }}>
            + Add to list
          </button>
        )}
      </div>
    </div>
  );
}
