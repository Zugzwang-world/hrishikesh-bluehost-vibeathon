// Coordinator placeholder: the whole flow without 3D. Lane D replaces this with the real Stage.
import { useEffect, useMemo, useState } from 'react'
import { DEFAULT_HOST, DEFAULT_LOOK, PERSONA, REQUIRED, SLOTS, type Slot } from './config'

type Merchant = { slug: string; name: string; code: string; tagline: string; brandColor: string; accentColor: string; logo: string }
type Product = { sku: string; merchant: string; name: string; slot: Slot; price: number; colorName: string; image: string; material: { color: string } }
type Catalog = { merchants: Merchant[]; products: Product[] }

const params = new URLSearchParams(location.search)
const embed = params.get('embed') === '1'
const host = (params.get('host') || DEFAULT_HOST || '').replace(/\/$/, '')

export default function App() {
  const [cat, setCat] = useState<Catalog | null>(null)
  const [look, setLook] = useState<Partial<Record<Slot, string>>>({})
  const [shop, setShop] = useState<string>('kaapi-club')

  useEffect(() => {
    fetch('/catalog/catalog.json').then(r => r.json()).then((c: Catalog) => {
      setCat(c)
      const bySku = new Map(c.products.map(p => [p.sku, p]))
      const skus = [...(params.get('look')?.split(',') ?? DEFAULT_LOOK), ...(params.get('try') ? [params.get('try')!] : [])]
      const l: Partial<Record<Slot, string>> = {}
      for (const s of skus) { const p = bySku.get(s.trim()); if (p) l[p.slot] = p.sku }
      setLook(l)
      const t = params.get('try') && bySku.get(params.get('try')!)
      if (t) setShop(t.merchant)
    })
  }, [])

  const bySku = useMemo(() => new Map(cat?.products.map(p => [p.sku, p]) ?? []), [cat])
  const items = SLOTS.map(s => look[s] && bySku.get(look[s]!)).filter(Boolean) as Product[]
  const total = items.reduce((a, p) => a + p.price, 0)
  const merchants = new Set(items.map(p => p.merchant)).size
  const title = 'Hrishikesh on stage'
  const bagUrl = host ? `${host}/cart?add=${items.map(p => p.sku).join(',')}&look=${encodeURIComponent(title)}` : null
  const color = (s: Slot) => (look[s] && bySku.get(look[s]!)?.material.color) || 'transparent'

  if (!cat) return <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>Loading the stage…</div>

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 340px', height: '100%' }}>
      <main style={{ position: 'relative', overflow: 'hidden', background: 'radial-gradient(circle at 50% 70%, #2a2440, var(--bg) 70%)' }}>
        {!embed && <header style={{ position: 'absolute', top: 16, left: 20, fontWeight: 700, letterSpacing: 2 }}>STAGE · {PERSONA.name}</header>}
        {/* placeholder avatar */}
        <div style={{ position: 'absolute', left: '50%', top: '12%', transform: 'translateX(-50%)', width: 160, display: 'grid', justifyItems: 'center', gap: 4 }}>
          <div style={{ width: 70, height: 26, borderRadius: '30px 30px 6px 6px', background: color('headwear') }} />
          <div style={{ width: 62, height: 70, borderRadius: 30, background: '#9b6e53', marginTop: -14 }} />
          <div style={{ width: 150, height: 170, borderRadius: 26, background: look.outerwear ? color('outerwear') : color('top'), display: 'grid', placeItems: 'center' }}>
            <div style={{ width: 56, height: 150, background: color('top'), borderRadius: 8 }} />
          </div>
          <div style={{ width: 130, height: 200, borderRadius: 16, background: color('bottom') }} />
          <div style={{ display: 'flex', gap: 14 }}>
            <div style={{ width: 62, height: 22, borderRadius: 10, background: color('footwear') }} />
            <div style={{ width: 62, height: 22, borderRadius: 10, background: color('footwear') }} />
          </div>
        </div>
        {/* shop ring */}
        <nav style={{ position: 'absolute', bottom: 150, left: 0, right: 0, display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
          {cat.merchants.map(m => (
            <button key={m.slug} onClick={() => setShop(m.slug)}
              style={{ border: 0, borderRadius: 999, padding: '8px 14px', background: shop === m.slug ? m.brandColor : 'var(--surface-2)', outline: shop === m.slug ? `2px solid ${m.accentColor}` : 'none' }}>
              {m.name}
            </button>
          ))}
        </nav>
        <div style={{ position: 'absolute', bottom: 12, left: 12, right: 12, display: 'flex', gap: 8, overflowX: 'auto' }}>
          {cat.products.filter(p => p.merchant === shop).map(p => (
            <button key={p.sku} onClick={() => setLook(l => ({ ...l, [p.slot]: p.sku }))}
              style={{ flex: '0 0 96px', border: look[p.slot] === p.sku ? '2px solid var(--accent)' : '2px solid transparent', borderRadius: 10, padding: 0, background: 'var(--surface)', overflow: 'hidden' }}>
              <img src={p.image} alt={p.name} style={{ width: '100%', display: 'block' }} />
            </button>
          ))}
        </div>
      </main>
      <aside style={{ background: 'var(--surface)', padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ color: 'var(--ink-dim)' }}>{PERSONA.event}</div>
        <h2 style={{ margin: 0 }}>{title}</h2>
        {SLOTS.map(s => {
          const p = look[s] && bySku.get(look[s]!)
          if (!p) return null
          const m = cat.merchants.find(x => x.slug === p.merchant)!
          return (
            <div key={s} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <span>{p.name} · {p.colorName}<br /><small style={{ color: 'var(--ink-dim)' }}>{m.name}</small></span>
              <span>₹{p.price.toLocaleString('en-IN')}{!REQUIRED.includes(s) && <button onClick={() => setLook(l => ({ ...l, [s]: undefined }))} style={{ marginLeft: 6, background: 'none', border: 0, color: 'var(--ink-dim)' }}>×</button>}</span>
            </div>
          )
        })}
        <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
          <span>{items.length} items · {merchants} merchants</span><span>₹{total.toLocaleString('en-IN')}</span>
        </div>
        {bagUrl ? (
          <a href={bagUrl} target="_top" onClick={() => window.parent.postMessage({ type: 'ensemble:add-look', skus: items.map(p => p.sku), look: title }, '*')}
            style={{ textAlign: 'center', background: 'var(--accent)', color: 'var(--accent-ink)', padding: 14, borderRadius: 'var(--radius)', fontWeight: 700, textDecoration: 'none' }}>
            Add look to bag
          </a>
        ) : (
          <div style={{ textAlign: 'center', background: 'var(--surface-2)', padding: 14, borderRadius: 'var(--radius)' }}>Bag: {items.map(p => p.sku).join(', ')}</div>
        )}
      </aside>
    </div>
  )
}
