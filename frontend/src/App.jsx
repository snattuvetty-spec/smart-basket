import { useState, useRef } from "react";

// ─── Price Database ──────────────────────────────────────────────────────────
const PRICES = {
  // ── Woolworths cheapest ──
  "Full Cream Milk 2L":       { woolworths: 2.49, coles: 3.30, aldi: 2.99 },
  "Skim Milk 2L":             { woolworths: 2.49, coles: 3.30, aldi: 2.89 },
  "Free Range Eggs 12pk":     { woolworths: 5.20, coles: 6.20, aldi: 5.49 },
  "Cage Eggs 12pk":           { woolworths: 3.50, coles: 4.20, aldi: 3.99 },
  "Olive Oil 750ml":          { woolworths: 5.99, coles: 8.50, aldi: 6.99 },
  "Rolled Oats 1kg":          { woolworths: 2.50, coles: 3.80, aldi: 2.99 },
  "Instant Coffee 200g":      { woolworths: 5.50, coles: 7.50, aldi: 5.99 },
  "Cornflakes 500g":          { woolworths: 3.49, coles: 5.20, aldi: 3.99 },
  "Dishwashing Liquid 500ml": { woolworths: 2.00, coles: 3.80, aldi: 2.99 },
  "Tomatoes 500g":            { woolworths: 2.49, coles: 3.80, aldi: 3.19 },
  // ── Coles cheapest ──
  "Chicken Breast 1kg":       { woolworths: 11.00, coles: 7.99, aldi: 8.99 },
  "Beef Mince 500g":          { woolworths: 8.00, coles: 5.99, aldi: 6.49 },
  "Baby Spinach 120g":        { woolworths: 3.50, coles: 2.50, aldi: 2.79 },
  "Toilet Paper 12pk":        { woolworths: 10.00, coles: 6.99, aldi: 7.99 },
  "Cheddar Cheese 500g":      { woolworths: 7.50, coles: 5.49, aldi: 5.99 },
  "Orange Juice 2L":          { woolworths: 5.50, coles: 3.49, aldi: 4.29 },
  "Tea Bags 100pk":           { woolworths: 5.00, coles: 3.49, aldi: 3.99 },
  "Baked Beans 420g":         { woolworths: 2.00, coles: 0.99, aldi: 1.29 },
  "Strawberry Jam 500g":      { woolworths: 4.00, coles: 2.49, aldi: 2.99 },
  "Frozen Peas 1kg":          { woolworths: 4.50, coles: 2.99, aldi: 3.49 },
  // ── Aldi cheapest ──
  "White Bread":              { woolworths: 3.00, coles: 2.80, aldi: 1.99 },
  "Sourdough Loaf":           { woolworths: 5.50, coles: 5.00, aldi: 3.99 },
  "Pasta 500g":               { woolworths: 2.50, coles: 2.20, aldi: 1.49 },
  "Canned Tomatoes 400g":     { woolworths: 1.80, coles: 1.60, aldi: 1.19 },
  "Basmati Rice 1kg":         { woolworths: 3.50, coles: 3.20, aldi: 2.49 },
  "Laundry Powder 2kg":       { woolworths: 12.00, coles: 11.50, aldi: 8.99 },
  "Apples 1kg":               { woolworths: 4.50, coles: 4.20, aldi: 3.49 },
  "Bananas 1kg":              { woolworths: 3.50, coles: 3.20, aldi: 2.89 },
  "Carrots 1kg":              { woolworths: 2.50, coles: 2.30, aldi: 1.99 },
  "Broccoli Each":            { woolworths: 3.50, coles: 3.20, aldi: 2.79 },
  "Greek Yoghurt 1kg":        { woolworths: 5.00, coles: 4.80, aldi: 3.99 },
  "Butter 250g":              { woolworths: 4.50, coles: 4.20, aldi: 3.49 },
  "Coffee Beans 500g":        { woolworths: 12.00, coles: 11.50, aldi: 8.99 },
  "Tuna Can 95g":             { woolworths: 2.50, coles: 2.30, aldi: 1.79 },
  "Peanut Butter 500g":       { woolworths: 5.00, coles: 4.80, aldi: 3.79 },
};

const STORE_CONFIG = {
  woolworths: { label: "Woolworths", color: "#00c6ff", bg: "rgba(0,198,255,0.12)",   pill: "#00c6ff",  emoji: "🟢" },
  coles:      { label: "Coles",      color: "#f87171", bg: "rgba(248,113,113,0.12)", pill: "#f87171",  emoji: "🔴" },
  aldi:       { label: "Aldi",       color: "#818cf8", bg: "rgba(129,140,248,0.12)", pill: "#818cf8",  emoji: "🔵" },
};

function getCheapest(name) {
  const p = PRICES[name];
  if (!p) return null;
  return Object.entries(p).reduce((a, b) => a[1] <= b[1] ? a : b)[0];
}

function totalSaved(items) {
  return items.reduce((sum, item) => {
    const p = PRICES[item.name];
    if (!p) return sum;
    const vals = Object.values(p);
    return sum + (Math.max(...vals) - Math.min(...vals)) * item.qty;
  }, 0);
}

let uid = 1;

export default function App() {
  const [view, setView] = useState("list");
  const [items, setItems] = useState([
    { id: uid++, name: "Full Cream Milk 2L",   qty: 2 },
    { id: uid++, name: "Free Range Eggs 12pk", qty: 1 },
    { id: uid++, name: "Chicken Breast 1kg",   qty: 1 },
    { id: uid++, name: "Pasta 500g",           qty: 2 },
    { id: uid++, name: "Canned Tomatoes 400g", qty: 3 },
    { id: uid++, name: "Olive Oil 750ml",      qty: 1 },
    { id: uid++, name: "Baby Spinach 120g",    qty: 1 },
    { id: uid++, name: "Toilet Paper 12pk",    qty: 1 },
  ]);

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: "#040d1a", minHeight: "100vh", maxWidth: 430, margin: "0 auto", display: "flex", flexDirection: "column" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 0; }
        input:focus { outline: none; }
        button { font-family: 'DM Sans', sans-serif; }

        .sb-bg {
          position: fixed; inset: 0; pointer-events: none; z-index: 0;
        }
        .sb-grid {
          position: absolute; inset: 0;
          background-image:
            linear-gradient(rgba(0,198,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,198,255,0.03) 1px, transparent 1px);
          background-size: 40px 40px;
        }
        .sb-glow {
          position: absolute;
          width: 400px; height: 300px;
          background: radial-gradient(circle, rgba(0,114,255,0.2), transparent 70%);
          top: -80px; right: -80px;
          border-radius: 50%;
          filter: blur(60px);
        }
        .sb-content { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; }

        .glass {
          background: rgba(255,255,255,0.05);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 12px;
          box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        }
        .item-card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 12px;
          transition: border-color 0.15s, background 0.15s;
        }
        .item-card:hover { background: rgba(0,198,255,0.05); border-color: rgba(0,198,255,0.2); }

        @keyframes slideUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
        .item-row { animation: slideUp 0.2s ease both; }

        @keyframes glow { 0%,100% { box-shadow: 0 4px 20px rgba(0,114,255,0.4); } 50% { box-shadow: 0 4px 32px rgba(0,198,255,0.6); } }
        .cta-btn { animation: glow 2.5s ease-in-out infinite; }
      `}</style>

      <div className="sb-bg"><div className="sb-grid" /><div className="sb-glow" /></div>
      <div className="sb-content">
        {view === "list"
          ? <ListView items={items} setItems={setItems} goCompare={() => setView("compare")} />
          : <CompareView items={items} goBack={() => setView("list")} />
        }
      </div>
    </div>
  );
}

function ListView({ items, setItems, goCompare }) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef();

  const suggestions = query.length > 0
    ? Object.keys(PRICES).filter(n => n.toLowerCase().includes(query.toLowerCase()) && !items.find(i => i.name === n)).slice(0, 6)
    : [];

  const addItem = (name) => {
    const existing = items.find(i => i.name === name);
    if (existing) {
      setItems(items.map(i => i.id === existing.id ? { ...i, qty: i.qty + 1 } : i));
    } else {
      setItems([...items, { id: uid++, name, qty: 1 }]);
    }
    setQuery("");
    inputRef.current?.focus();
  };

  const remove = (id) => setItems(items.filter(i => i.id !== id));
  const changeQty = (id, d) => setItems(items.map(i => i.id === id ? { ...i, qty: Math.max(1, i.qty + d) } : i));
  const savings = totalSaved(items);
  const knownCount = items.filter(i => PRICES[i.name]).length;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "28px 20px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 22 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #0072ff, #00c6ff)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, boxShadow: "0 4px 14px rgba(0,114,255,0.4)" }}>🛒</div>
          <div>
            <div style={{ color: "#00c6ff", fontSize: 18, fontWeight: 800, fontFamily: "'Syne', sans-serif", lineHeight: 1 }}>SmartBasket</div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 10, letterSpacing: 2, textTransform: "uppercase" }}>by Natts Digital</div>
          </div>
        </div>
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

      {/* Search */}
      <div style={{ padding: "0 20px 16px" }}>
        <div style={{ position: "relative" }}>
          <div className="glass" style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderColor: focused ? "rgba(0,198,255,0.35)" : "rgba(255,255,255,0.08)", transition: "border-color 0.2s" }}>
            <span style={{ color: "rgba(0,198,255,0.45)", fontSize: 15 }}>🔍</span>
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 150)}
              onKeyDown={e => e.key === "Enter" && query.trim() && (suggestions[0] ? addItem(suggestions[0]) : addItem(query.trim()))}
              placeholder="Search or add item…"
              style={{ flex: 1, background: "none", border: "none", color: "#fff", fontSize: 14, fontWeight: 500 }}
            />
            {query && <button onClick={() => setQuery("")} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 18 }}>×</button>}
          </div>
          {suggestions.length > 0 && (
            <div style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, background: "#0a1628", border: "1px solid rgba(0,198,255,0.15)", borderRadius: 12, overflow: "hidden", boxShadow: "0 8px 32px rgba(0,0,0,0.5)", zIndex: 50 }}>
              {suggestions.map((s, i) => {
                const cheap = getCheapest(s);
                const cfg = cheap ? STORE_CONFIG[cheap] : null;
                return (
                  <button key={s} onMouseDown={() => addItem(s)}
                    style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 16px", background: "none", border: "none", cursor: "pointer", borderBottom: i < suggestions.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none", color: "#fff", textAlign: "left" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(0,198,255,0.07)"}
                    onMouseLeave={e => e.currentTarget.style.background = "none"}
                  >
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{s}</span>
                    {cfg && <span style={{ fontSize: 11, color: cfg.color, fontWeight: 700, background: cfg.bg, padding: "2px 8px", borderRadius: 6 }}>Best: ${PRICES[s][cheap].toFixed(2)}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* List */}
      <div style={{ flex: 1, padding: "0 16px", overflowY: "auto" }}>
        {items.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🛒</div>
            <div style={{ fontWeight: 600, color: "rgba(255,255,255,0.4)" }}>Your list is empty</div>
            <div style={{ fontSize: 13, marginTop: 6, color: "rgba(255,255,255,0.2)" }}>Search above to add items</div>
          </div>
        ) : items.map((item, idx) => {
          const p = PRICES[item.name];
          const cheap = getCheapest(item.name);
          const cfg = cheap ? STORE_CONFIG[cheap] : null;
          return (
            <div key={item.id} className="item-row item-card" style={{ animationDelay: `${idx * 0.04}s`, padding: "13px 14px", marginBottom: 8, display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: cfg?.pill || "rgba(255,255,255,0.15)", flexShrink: 0, boxShadow: cfg ? `0 0 6px ${cfg.pill}88` : "none" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.88)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.name}</div>
                {cfg && p
                  ? <div style={{ fontSize: 11, color: cfg.color, fontWeight: 600, marginTop: 2 }}>{cfg.emoji} {cfg.label} · <span style={{ fontFamily: "'DM Mono', monospace" }}>${p[cheap].toFixed(2)}</span> ea</div>
                  : <div style={{ fontSize: 11, color: "rgba(255,255,255,0.2)", marginTop: 2 }}>No price data</div>
                }
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

      {/* CTA */}
      {knownCount > 0 && (
        <div style={{ padding: "16px 16px 32px" }}>
          <button className="cta-btn" onClick={goCompare} style={{ width: "100%", padding: "15px", borderRadius: 12, border: "none", background: "linear-gradient(135deg, #0072ff, #00c6ff)", color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <span>Compare Prices</span>
            <span style={{ background: "rgba(255,255,255,0.2)", borderRadius: 8, padding: "3px 10px", fontSize: 13, fontWeight: 800, fontFamily: "'DM Mono', monospace" }}>Save ${savings.toFixed(2)}</span>
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
    const cheap = getCheapest(item.name);
    (groups[cheap] || groups.unknown).push(item);
  });

  const storeOrder = ["woolworths", "coles", "aldi"].sort((a, b) => groups[b].length - groups[a].length);
  const storeTotals = {};
  storeOrder.forEach(store => {
    storeTotals[store] = groups[store].reduce((sum, item) => sum + (PRICES[item.name]?.[store] || 0) * item.qty, 0);
  });

  const grandTotal = Object.values(storeTotals).reduce((a, b) => a + b, 0);
  const savings = totalSaved(items);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "28px 20px 16px" }}>
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

      {/* Store bars */}
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

      {/* Store groups */}
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
                  const p = PRICES[item.name];
                  const storePrice = p?.[store];
                  const others = p ? Object.entries(p).filter(([s]) => s !== store).sort((a, b) => a[1] - b[1]) : [];
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
            <div style={{ fontSize: 12, color: "#fbbf24", fontWeight: 600, marginBottom: 8 }}>⚠️ No price data for:</div>
            {groups.unknown.map(item => <div key={item.id} style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", padding: "4px 0" }}>{item.name}</div>)}
          </div>
        )}

        {/* Summary */}
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
