import { useStore } from '../store'
import type { Merchant } from '../api/types'

/** Merchant shops as an orbit of badges around the avatar (2D overlay; a scroll row on phones via CSS). */
export function ShopRing() {
  const catalog = useStore(s => s.catalog)
  const shop = useStore(s => s.shop)
  const setShop = useStore(s => s.setShop)
  const look = useStore(s => s.look)
  if (!catalog) return null
  const ms = catalog.merchants
  const worn = new Set(Object.values(look).filter(Boolean).map(sku => catalog.products.find(p => p.sku === sku)?.merchant))
  const rows = Math.ceil(ms.length / 2)
  return (
    <nav className="shop-ring" aria-label="Shops">
      <div className="shop-ring__orbit" aria-hidden />
      {ms.map((m, i) => {
        const side = i % 2 === 0 ? -1 : 1
        const row = Math.floor(i / 2)
        const rowsOnSide = side < 0 ? rows : Math.floor(ms.length / 2)
        const fy = rowsOnSide > 1 ? row / (rowsOnSide - 1) : 0.5
        const y = 16 + fy * 58
        const dy = (y - 47) / 52
        const x = 50 + side * 38 * Math.sqrt(Math.max(0, 1 - dy * dy))
        return <Badge key={m.slug} m={m} active={shop === m.slug} worn={worn.has(m.slug)} x={x} y={y} i={i} onPick={() => setShop(shop === m.slug ? null : m.slug)} />
      })}
    </nav>
  )
}

function Badge({ m, active, worn, x, y, i, onPick }: { m: Merchant; active: boolean; worn: boolean; x: number; y: number; i: number; onPick: () => void }) {
  return (
    <button
      className={'shop-badge' + (active ? ' is-active' : '') + (worn ? ' is-worn' : '')}
      style={{ left: `${x}%`, top: `${y}%`, ['--brand' as string]: m.brandColor, ['--brand-accent' as string]: m.accentColor, ['--i' as string]: i }}
      onClick={onPick}
      aria-pressed={active}
      title={`${m.name} · ${m.tagline}`}
    >
      <span className="shop-badge__disc">
        <img src={m.logo} alt="" onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none' }} />
        <span className="shop-badge__code">{m.code}</span>
      </span>
      <span className="shop-badge__name">{m.name}</span>
    </button>
  )
}
