import { useEffect, useRef } from 'react'
import { REQUIRED } from '../config'
import { inr } from '../lib/bag'
import { useStore } from '../store'

/** The open shop's products. Click or arrow keys to equip (left/right), up/down switches shop. */
export function ProductRail() {
  const catalog = useStore(s => s.catalog)
  const shop = useStore(s => s.shop)
  const look = useStore(s => s.look)
  const equip = useStore(s => s.equip)
  const clear = useStore(s => s.clear)
  const setShop = useStore(s => s.setShop)
  const mode = useStore(s => s.mode)
  const rail = useRef<HTMLDivElement>(null)
  const merchant = catalog?.merchants.find(m => m.slug === shop)
  const products = catalog && shop ? catalog.products.filter(p => p.merchant === shop) : []

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      const st = useStore.getState()
      if (!st.catalog || st.mode !== 'fit') return
      const ms = st.catalog.merchants
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        const i = ms.findIndex(m => m.slug === st.shop)
        const n = (i + (e.key === 'ArrowDown' ? 1 : -1) + ms.length) % ms.length
        st.setShop(ms[n < 0 ? 0 : n].slug); e.preventDefault(); return
      }
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      const ps = st.catalog.products.filter(p => p.merchant === st.shop)
      if (!ps.length) return
      const cur = ps.findIndex(p => st.look[p.slot] === p.sku)
      const n = cur < 0 ? 0 : (cur + (e.key === 'ArrowRight' ? 1 : -1) + ps.length) % ps.length
      st.equip(ps[n].sku)
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    const el = rail.current?.querySelector('.product-card.is-on') as HTMLElement | null
    el?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' })
  }, [look, shop])

  if (!merchant || mode !== 'fit') return null
  return (
    <section className="product-rail" style={{ ['--brand' as string]: merchant.brandColor, ['--brand-accent' as string]: merchant.accentColor }} aria-label={`${merchant.name} products`}>
      <header className="product-rail__head">
        <strong>{merchant.name}</strong>
        <span>{merchant.tagline}</span>
        <button className="icon-btn" onClick={() => setShop(null)} aria-label="Close shop">×</button>
      </header>
      <div className="product-rail__list" ref={rail}>
        {products.map(p => {
          const on = look[p.slot] === p.sku
          return (
            <button key={p.sku} className={'product-card' + (on ? ' is-on' : '')} aria-pressed={on}
              onClick={() => (on && !REQUIRED.includes(p.slot) ? clear(p.slot) : equip(p.sku))}>
              <span className="product-card__img"><img src={p.image} alt="" loading="lazy" /></span>
              <span className="product-card__name">{p.name}</span>
              <span className="product-card__meta">{p.colorName} · {inr(p.price)}</span>
              {on && <span className="product-card__tag">On</span>}
            </button>
          )
        })}
      </div>
    </section>
  )
}
