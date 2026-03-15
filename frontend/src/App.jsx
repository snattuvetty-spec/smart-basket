import { useState, useRef, useEffect, useCallback } from "react";
import SpecialsPage from "./SpecialsPage";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";
const LOGIN_URL = `${API}/login`;

const STORE_CONFIG = {
  woolworths: { label: "Woolworths", color: "#00c6ff", bg: "rgba(0,198,255,0.12)", pill: "#00c6ff", emoji: "🟢" },
  coles:      { label: "Coles",      color: "#f87171", bg: "rgba(248,113,113,0.12)", pill: "#f87171", emoji: "🔴" },
  aldi:       { label: "Aldi",       color: "#818cf8", bg: "rgba(129,140,248,0.12)", pill: "#818cf8", emoji: "🔵" },
};

function getCheapest(prices) {
  if (!prices) return null;
  return Object.entries(prices).reduce((a, b) => a[1] <= b[1] ? a : b)[0];
}

function totalSaved(items) {
  return items.reduce((sum, item) => {
    const p = item.prices;
    if (!p) return sum;
    const vals = Object.values(p);
    return sum + (Math.max(...vals) - Math.min(...vals)) * item.qty;
  }, 0);
}

let uid = 1;

// ── Auth helpers ──────────────────────────────────────────────────────────────
function getSessionToken() { return localStorage.getItem('sp_session_token'); }
function getUser() {
  const u = localStorage.getItem('sp_user');
  return u ? JSON.parse(u) : null;
}
function setSession(token, user) {
  localStorage.setItem('sp_session_token', token);
  localStorage.setItem('sp_user', JSON.stringify(user));
}
function clearSession() {
  localStorage.removeItem('sp_session_token');
  localStorage.removeItem('sp_user');
}
function authHeaders() {
  const token = getSessionToken();
  return token ? { 'X-Auth-Token': token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export default function App() {
  const [authState, setAuthState] = useState('checking'); // 'checking' | 'authed' | 'unauthed'
  const [user, setUser]           = useState(null);
  const [tab, setTab]             = useState("specials");
  const [items, setItems]         = useState([]);
  const [loadingPrices, setLoadingPrices] = useState(false);

  // ── Auth check on load ──────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      // Check for auth_token in URL (coming back from login page)
      const params = new URLSearchParams(window.location.search);
      const authToken = params.get('auth_token');

      if (authToken) {
        // Exchange auth token for session token
        try {
          const res = await fetch(`${API}/api/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: authToken }),
          });
          const data = await res.json();
          if (data.valid) {
            setSession(data.session_token, { username: data.username, name: data.name });
            setUser({ username: data.username, name: data.name });
            setAuthState('authed');
            // Clean URL
            window.history.replaceState({}, '', '/');
            // Load saved list
            loadSavedList();
            return;
          }
        } catch (e) {
          console.error('Token exchange failed:', e);
        }
      }

      // Check existing session
      const sessionToken = getSessionToken();
      const cachedUser = getUser();
      if (sessionToken && cachedUser) {
        setUser(cachedUser);
        setAuthState('authed');
        loadSavedList();
        return;
      }

      // Not logged in — redirect to login
      setAuthState('unauthed');
      window.location.href = LOGIN_URL;
    };

    init();
  }, []);

  const loadSavedList = async () => {
    try {
      const res = await fetch(`${API}/api/list/load`, { headers: authHeaders() });
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        const loaded = data.items.map(row => ({
          id:      uid++,
          name:    row.name,
          qty:     1,
          prices:  row.store && row.price ? { [row.store]: row.price } : null,
          special: row.price ? {
            price:      row.price,
            was_price:  row.was_price,
            saving_pct: row.saving_pct,
            store:      row.store,
          } : null,
        }));
        setItems(loaded);
        // Also fetch cross-store prices from Flask
        setLoadingPrices(true);
        try {
          const priceRes = await fetch(`${API}/api/prices`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items: data.items.map(r => r.name) }),
          });
          const priceData = await priceRes.json();
          setItems(loaded.map(item => ({
            ...item,
            prices: priceData[item.name] || item.prices,
          })));
        } catch (e) {
          console.error('Price fetch failed:', e);
        } finally {
          setLoadingPrices(false);
        }
      }
    } catch (e) {
      console.error('Load list failed:', e);
    }
  };

  const saveList = useCallback(async (currentItems) => {
    try {
      await fetch(`${API}/api/list/save`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          items: currentItems.map(i => ({
            name:       i.name,
            price:      i.special?.price || null,
            was_price:  i.special?.was_price || null,
            saving_pct: i.special?.saving_pct || null,
            store:      i.special?.store || null,
          }))
        }),
      });
    } catch (e) {
      console.error('Save list failed:', e);
    }
  }, []);

  const handleLogout = async () => {
    try {
      await fetch(`${API}/api/logout`, { method: 'POST', headers: authHeaders() });
    } catch (e) {}
    clearSession();
    window.location.href = LOGIN_URL;
  };

  const fetchPrices = useCallback(async (currentItems) => {
    const names = currentItems.map(i => i.name);
    if (names.length === 0) return;
    setLoadingPrices(true);
    try {
      const res = await fetch(`${API}/api/prices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: names }),
      });
      const data = await res.json();
      setItems(prev => prev.map(item => ({
        ...item,
        prices: data[item.name] || null,
      })));
    } catch (err) {
      console.error("Failed to fetch prices:", err);
    } finally {
      setLoadingPrices(false);
    }
  }, []);

  const addItem = (name, existingItems) => {
    let newItems;
    const existing = existingItems.find(i => i.name === name);
    if (existing) {
      newItems = existingItems.map(i => i.id === existing.id ? { ...i, qty: i.qty + 1 } : i);
    } else {
      newItems = [...existingItems, { id: uid++, name, qty: 1, prices: null }];
      fetch(`${API}/api/prices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: [name] }),
      }).then(r => r.json()).then(data => {
        setItems(prev => prev.map(i => i.name === name ? { ...i, prices: data[name] || null } : i));
      }).catch(console.error);
    }
    setItems(newItems);
    saveList(newItems);
    return newItems;
  };

  const handleAddFromSpecials = (name, special) => {
    const prices = special?.price && special?.store ? { [special.store]: special.price } : null;
    const existing = items.find(i => i.name === name);
    let newItems;
    if (existing) {
      newItems = items.map(i => i.id === existing.id ? { ...i, qty: i.qty + 1, prices: prices || i.prices, special: special || i.special } : i);
    } else {
      newItems = [...items, { id: uid++, name, qty: 1, prices, special: special || null }];
    }
    setItems(newItems);
    saveList(newItems);
    setTab("list");
  };

  // ── Loading / redirect state ──────────────────────────────────────────────
  if (authState === 'checking' || authState === 'unauthed') {
    return (
      <div style={{ fontFamily: "'DM Sans', sans-serif", background: "#040d1a", minHeight: "100vh", maxWidth: 430, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", color: "rgba(255,255,255,0.4)" }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>🛒</div>
          <div style={{ fontSize: 14 }}>{authState === 'unauthed' ? 'Redirecting to login...' : 'Loading...'}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: "#040d1a", minHeight: "100vh", maxWidth: 430, margin: "0 auto", display: "flex", flexDirection: "column" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 0; }
        input:focus { outline: none; }
        button { font-family: 'DM Sans', sans-serif; }
        .sb-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
        .sb-grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(0,198,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,198,255,0.03) 1px, transparent 1px); background-size: 40px 40px; }
        .sb-glow { position: absolute; width: 400px; height: 300px; background: radial-gradient(circle, rgba(0,114,255,0.2), transparent 70%); top: -80px; right: -80px; border-radius: 50%; filter: blur(60px); }
        .sb-content { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .glass { background: rgba(255,255,255,0.05); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
        .item-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; transition: border-color 0.15s, background 0.15s; }
        .item-card:hover { background: rgba(0,198,255,0.05); border-color: rgba(0,198,255,0.2); }
        @keyframes slideUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
        .item-row { animation: slideUp 0.2s ease both; }
        @keyframes glow { 0%,100% { box-shadow: 0 4px 20px rgba(0,114,255,0.4); } 50% { box-shadow: 0 4px 32px rgba(0,198,255,0.6); } }
        .cta-btn { animation: glow 2.5s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner { animation: spin 0.8s linear infinite; }
        .bottom-nav { position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 430px; background: rgba(4,13,26,0.95); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid rgba(255,255,255,0.07); display: flex; z-index: 100; }
        .nav-btn { flex: 1; padding: 12px 4px 16px; display: flex; flex-direction: column; align-items: center; gap: 4px; background: none; border: none; cursor: pointer; transition: all 0.15s; }
        .nav-btn .nav-icon { font-size: 20px; transition: transform 0.15s; }
        .nav-btn .nav-label { font-size: 10px; font-weight: 600; letter-spacing: 0.5px; color: rgba(255,255,255,0.28); font-family: 'DM Sans', sans-serif; transition: color 0.15s; }
        .nav-btn.active .nav-label { color: #00c6ff; }
        .nav-btn.active .nav-icon { transform: scale(1.15); }
      `}</style>

      <div className="sb-bg"><div className="sb-grid" /><div className="sb-glow" /></div>

      {/* Header */}
      <div style={{ position: "relative", zIndex: 1, padding: "16px 20px 0", display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: "linear-gradient(135deg, #0072ff, #00c6ff)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17, boxShadow: "0 4px 14px rgba(0,114,255,0.4)" }}>🛒</div>
        <div>
          <div style={{ color: "#00c6ff", fontSize: 17, fontWeight: 800, fontFamily: "'Syne', sans-serif", lineHeight: 1 }}>SmartPicks</div>
          <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 9, letterSpacing: 2, textTransform: "uppercase" }}>by Natts Digital</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {loadingPrices && <div style={{ width: 16, height: 16, border: "2px solid rgba(0,198,255,0.2)", borderTopColor: "#00c6ff", borderRadius: "50%" }} className="spinner" />}
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, fontWeight: 600 }}>Hi, {user?.name?.split(' ')[0]}</div>
          <button onClick={handleLogout} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "rgba(255,255,255,0.4)", fontSize: 11, padding: "4px 10px", cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}>Logout</button>
        </div>
      </div>

      {/* Page content */}
      <div className="sb-content" style={{ paddingBottom: 68 }}>
        {tab === "specials" && <SpecialsPage onAddToList={handleAddFromSpecials} />}
        {tab === "list" && <ListView items={items} setItems={setItems} addItem={addItem} loadingPrices={loadingPrices} goCompare={() => setTab("compare")} saveList={saveList} />}
        {tab === "compare" && <CompareView items={items} goBack={() => setTab("list")} />}
      </div>

      {/* Bottom nav */}
      <nav className="bottom-nav">
        <button className={`nav-btn ${tab === "specials" ? "active" : ""}`} onClick={() => setTab("specials")}>
          <span className="nav-icon">🏷️</span>
          <span className="nav-label">SPECIALS</span>
        </button>
        <button className={`nav-btn ${tab === "list" ? "active" : ""}`} onClick={() => setTab("list")}>
          <span className="nav-icon">📋</span>
          <span className="nav-label">MY LIST{items.length > 0 ? ` (${items.length})` : ""}</span>
        </button>
        <button className={`nav-btn ${tab === "compare" ? "active" : ""}`} onClick={() => setTab("compare")}>
          <span className="nav-icon">⚖️</span>
          <span className="nav-label">COMPARE</span>
        </button>
      </nav>
    </div>
  );
}

function ListView({ items, setItems, addItem, loadingPrices, goCompare, saveList }) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const inputRef = useRef();

  useEffect(() => {
    if (query.length < 1) { setSuggestions([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data.filter(s => !items.find(i => i.name === s)).slice(0, 6));
      } catch { setSuggestions([]); }
    }, 200);
    return () => clearTimeout(timer);
  }, [query, items]);

  const handleAdd = (name) => {
    addItem(name, items);
    setQuery("");
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const remove = (id) => {
    const newItems = items.filter(i => i.id !== id);
    setItems(newItems);
    saveList(newItems);
  };
  const changeQty = (id, d) => setItems(prev => prev.map(i => i.id === id ? { ...i, qty: Math.max(1, i.qty + d) } : i));
  const savings = totalSaved(items);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px 20px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>Shopping List</div>
            <div style={{ color: "#fff", fontSize: 28, fontWeight: 800, fontFamily: "'Syne', sans-serif" }}>{items.length} item{items.length !== 1 ? "s" : ""}</div>
          </div>
          {savings > 0 && (
            <div className="glass" style={{ padding: "10px 14px", textAlign: "right", borderColor: "rgba(251,191,36,0.2)" }}>
              <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 10, fontWeight: 600, letterSpacing: 1 }}>POTENTIAL SAVING</div>
              <div style={{ color: "#fbbf24", fontSize: 20, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>${savings.toFixed(2)}</div>
            </div>
          )}
        </div>
      </div>

      <div style={{ padding: "0 20px 16px" }}>
        <div style={{ position: "relative" }}>
          <div className="glass" style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderColor: focused ? "rgba(0,198,255,0.35)" : "rgba(255,255,255,0.08)", transition: "border-color 0.2s" }}>
            <span style={{ color: "rgba(0,198,255,0.45)", fontSize: 15 }}>🔍</span>
            <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)} onFocus={() => setFocused(true)} onBlur={() => setTimeout(() => setFocused(false), 150)} onKeyDown={e => e.key === "Enter" && query.trim() && (suggestions[0] ? handleAdd(suggestions[0]) : handleAdd(query.trim()))} placeholder="Search or add item…" style={{ flex: 1, background: "none", border: "none", color: "#fff", fontSize: 14, fontWeight: 500 }} />
            {query && <button onClick={() => { setQuery(""); setSuggestions([]); }} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 18 }}>×</button>}
          </div>
          {suggestions.length > 0 && (
            <div style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, background: "#0a1628", border: "1px solid rgba(0,198,255,0.15)", borderRadius: 12, overflow: "hidden", boxShadow: "0 8px 32px rgba(0,0,0,0.5)", zIndex: 50 }}>
              {suggestions.map((s, i) => (
                <button key={s} onMouseDown={() => handleAdd(s)} style={{ width: "100%", display: "flex", alignItems: "center", padding: "11px 16px", background: "none", border: "none", cursor: "pointer", borderBottom: i < suggestions.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none", color: "#fff", textAlign: "left" }} onMouseEnter={e => e.currentTarget.style.background = "rgba(0,198,255,0.07)"} onMouseLeave={e => e.currentTarget.style.background = "none"}>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{s}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ flex: 1, padding: "0 16px", overflowY: "auto" }}>
        {items.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🛒</div>
            <div style={{ fontWeight: 600, color: "rgba(255,255,255,0.4)" }}>Your list is empty</div>
            <div style={{ fontSize: 13, marginTop: 6, color: "rgba(255,255,255,0.2)" }}>Browse Specials to add items</div>
          </div>
        ) : items.map((item, idx) => {
          const cheap = getCheapest(item.prices);
          const cfg = cheap ? STORE_CONFIG[cheap] : null;
          return (
            <div key={item.id} className="item-row item-card" style={{ animationDelay: `${idx * 0.04}s`, padding: "13px 14px", marginBottom: 8, display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: cfg?.pill || "rgba(255,255,255,0.15)", flexShrink: 0, boxShadow: cfg ? `0 0 6px ${cfg.pill}88` : "none" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.88)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.name}</div>
                {cfg && item.prices ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 11, color: cfg.color, fontWeight: 600 }}>{cfg.emoji} {cfg.label} · <span style={{ fontFamily: "'DM Mono', monospace" }}>${item.prices[cheap].toFixed(2)}</span></span>
                    {item.special?.was_price && <span style={{ fontSize: 10, color: "rgba(255,255,255,0.28)", textDecoration: "line-through" }}>${item.special.was_price.toFixed(2)}</span>}
                    {item.special?.saving_pct && <span style={{ fontSize: 10, color: "#4ade80", fontWeight: 700 }}>-{Math.round(item.special.saving_pct)}%</span>}
                  </div>
                ) : <div style={{ fontSize: 11, color: "rgba(255,255,255,0.2)", marginTop: 2 }}>{loadingPrices ? "Fetching price…" : "No price data"}</div>}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <button onClick={() => changeQty(item.id, -1)} style={{ width: 28, height: 28, borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", cursor: "pointer", fontSize: 15, color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>−</button>
                <span style={{ width: 20, textAlign: "center", fontWeight: 700, fontSize: 14, color: "#fff", fontFamily: "'DM Mono', monospace" }}>{item.qty}</span>
                <button onClick={() => changeQty(item.id, 1)} style={{ width: 28, height: 28, borderRadius: 7, border: "1px solid rgba(0,198,255,0.3)", background: "rgba(0,198,255,0.1)", cursor: "pointer", fontSize: 15, color: "#00c6ff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>+</button>
              </div>
              <button onClick={() => remove(item.id)} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.18)", cursor: "pointer", fontSize: 18, padding: "0 2px", flexShrink: 0 }}>×</button>
            </div>
          );
        })}
        <div style={{ height: 16 }} />
      </div>

      {items.length > 0 && (
        <div style={{ padding: "16px 16px 8px" }}>
          <button className="cta-btn" onClick={goCompare} style={{ width: "100%", padding: "15px", borderRadius: 12, border: "none", background: "linear-gradient(135deg, #0072ff, #00c6ff)", color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <span>Compare Prices</span>
            {savings > 0 && <span style={{ background: "rgba(255,255,255,0.2)", borderRadius: 8, padding: "3px 10px", fontSize: 13, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>Save ${savings.toFixed(2)}</span>}
            <span>→</span>
          </button>
        </div>
      )}
    </div>
  );
}

function CompareView({ items, goBack }) {
  const groups = { woolworths: [], coles: [], aldi: [], unknown: [] };
  items.forEach(item => {
    const cheap = getCheapest(item.prices);
    (groups[cheap] || groups.unknown).push(item);
  });

  const storeOrder = ["woolworths", "coles", "aldi"].sort((a, b) => groups[b].length - groups[a].length);
  const storeTotals = {};
  storeOrder.forEach(store => {
    storeTotals[store] = groups[store].reduce((sum, item) => sum + (item.prices?.[store] || 0) * item.qty, 0);
  });

  const grandTotal = Object.values(storeTotals).reduce((a, b) => a + b, 0);
  const savings = totalSaved(items);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px 20px 16px" }}>
        <button onClick={goBack} style={{ background: "none", border: "none", color: "rgba(0,198,255,0.65)", cursor: "pointer", fontSize: 13, fontWeight: 600, marginBottom: 16, padding: 0, display: "flex", alignItems: "center", gap: 4 }}>← Back to list</button>
        <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>Smart Price Split</div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div style={{ color: "#fff", fontSize: 32, fontWeight: 800, fontFamily: "'Syne', sans-serif", lineHeight: 1 }}>${grandTotal.toFixed(2)}</div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 12, marginTop: 4 }}>across {storeOrder.filter(s => groups[s].length > 0).length} stores</div>
          </div>
          <div className="glass" style={{ padding: "10px 16px", textAlign: "right", borderColor: "rgba(251,191,36,0.2)" }}>
            <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 10, fontWeight: 600, letterSpacing: 1 }}>YOU SAVE</div>
            <div style={{ color: "#fbbf24", fontSize: 22, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>${savings.toFixed(2)}</div>
            <div style={{ color: "rgba(255,255,255,0.2)", fontSize: 10 }}>vs single-store shop</div>
          </div>
        </div>
      </div>

      <div style={{ padding: "0 20px 16px", display: "flex", gap: 8 }}>
        {storeOrder.map(store => {
          const cfg = STORE_CONFIG[store];
          const count = groups[store].length;
          const pct = items.length > 0 ? (count / items.length) * 100 : 0;
          return (
            <div key={store} className="glass" style={{ flex: 1, padding: "10px 10px 8px", position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", bottom: 0, left: 0, width: `${pct}%`, height: 2, background: cfg.pill }} />
              <div style={{ fontSize: 11, fontWeight: 700, color: cfg.color }}>{cfg.label}</div>
              <div style={{ color: "#fff", fontSize: 16, fontWeight: 800, marginTop: 2, fontFamily: "'DM Mono', monospace" }}>{count}</div>
              <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 10 }}>item{count !== 1 ? "s" : ""}</div>
            </div>
          );
        })}
      </div>

      <div style={{ flex: 1, padding: "0 16px 24px", overflowY: "auto" }}>
        {storeOrder.map((store, storeIdx) => {
          const cfg = STORE_CONFIG[store];
          const storeItems = groups[store];
          if (storeItems.length === 0) return null;
          return (
            <div key={store} className="item-row" style={{ animationDelay: `${storeIdx * 0.08}s`, marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 9, background: cfg.bg, border: `1px solid ${cfg.color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>{cfg.emoji}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: cfg.color }}>{cfg.label}</div>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>{storeItems.length} item{storeItems.length !== 1 ? "s" : ""} · cheapest here</div>
                  </div>
                </div>
                <div style={{ fontSize: 17, fontWeight: 800, color: cfg.color, fontFamily: "'DM Mono', monospace" }}>${storeTotals[store].toFixed(2)}</div>
              </div>
              <div className="glass" style={{ overflow: "hidden" }}>
                {storeItems.map((item, idx) => {
                  const storePrice = item.prices?.[store];
                  const others = item.prices ? Object.entries(item.prices).filter(([s]) => s !== store).sort((a, b) => a[1] - b[1]) : [];
                  return (
                    <div key={item.id} style={{ padding: "11px 14px", borderBottom: idx < storeItems.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.name}</div>
                        <div style={{ display: "flex", gap: 4, marginTop: 5, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 10, fontWeight: 700, background: cfg.bg, color: cfg.color, borderRadius: 5, padding: "2px 7px", border: `1px solid ${cfg.color}33` }}>{cfg.label} ${storePrice?.toFixed(2)} ✓</span>
                          {others.map(([s, price]) => (
                            <span key={s} style={{ fontSize: 10, fontWeight: 500, background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.28)", borderRadius: 5, padding: "2px 7px" }}>{STORE_CONFIG[s].label} ${price.toFixed(2)}</span>
                          ))}
                        </div>
                      </div>
                      <div style={{ textAlign: "right", flexShrink: 0 }}>
                        {storePrice && <div style={{ fontSize: 14, fontWeight: 800, color: cfg.color, fontFamily: "'DM Mono', monospace" }}>${(storePrice * item.qty).toFixed(2)}</div>}
                        {item.qty > 1 && <div style={{ fontSize: 10, color: "rgba(255,255,255,0.28)" }}>×{item.qty}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {groups.unknown.length > 0 && (
          <div className="glass" style={{ padding: 14, marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "#fbbf24", fontWeight: 600, marginBottom: 8 }}>No price data for:</div>
            {groups.unknown.map(item => <div key={item.id} style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", padding: "4px 0" }}>{item.name}</div>)}
          </div>
        )}

        <div className="glass" style={{ padding: 16, borderColor: "rgba(0,198,255,0.12)" }}>
          <div style={{ color: "rgba(0,198,255,0.55)", fontSize: 11, fontWeight: 700, letterSpacing: 1, marginBottom: 12, textTransform: "uppercase" }}>Summary</div>
          {storeOrder.map(store => groups[store].length > 0 && (
            <div key={store} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ color: "rgba(255,255,255,0.45)", fontSize: 13 }}>{STORE_CONFIG[store].label} ({groups[store].length} items)</span>
              <span style={{ color: "rgba(255,255,255,0.8)", fontWeight: 700, fontSize: 13, fontFamily: "'DM Mono', monospace" }}>${storeTotals[store].toFixed(2)}</span>
            </div>
          ))}
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", marginTop: 10, paddingTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#fff", fontWeight: 700 }}>Total</span>
            <span style={{ color: "#00c6ff", fontSize: 22, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>${grandTotal.toFixed(2)}</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: "rgba(255,255,255,0.22)", textAlign: "center" }}>
            Saving <span style={{ color: "#fbbf24" }}>${savings.toFixed(2)}</span> vs single-store shopping
          </div>
        </div>
        <div style={{ height: 8 }} />
      </div>
    </div>
  );
}
