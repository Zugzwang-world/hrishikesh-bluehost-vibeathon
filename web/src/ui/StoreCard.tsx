import { REQUIRED, SLOTS, type Slot } from '../config'
import type { Merchant, Product } from '../api/types'
import { instagram, thriftTags } from '../lib/bag'
import { useStore } from '../store'

export const SLOT_LABEL: Record<Slot, string> = { top: 'Top', outerwear: 'Layer', bottom: 'Bottom', footwear: 'Shoes', headwear: 'Head', eyewear: 'Eyes', watch: 'Wrist', neckwear: 'Neck' }

/** A store beside the stage: the piece(s) worn from it, with previous/next to swap on the avatar. Click opens its rail. */
export function StoreCard({ m, index, strip }: { m: Merchant; index: number; strip?: boolean }) {
  const catalog = useStore(s => s.catalog)
  const shop = useStore(s => s.shop)
  const setShop = useStore(s => s.setShop)
  if (!catalog) return null
  const products = catalog.products.filter(p => p.merchant === m.slug)
  const slots = SLOTS.filter(s => products.some(p => p.slot === s))
  const open = shop === m.slug
  const ig = instagram(m)
  return (
    <section className={'store-card' + (open ? ' is-open' : '') + (strip ? ' store-card--strip' : '')}
      style={{ ['--brand' as string]: m.brandColor, ['--brand-accent' as string]: m.accentColor, ['--i' as string]: index }}>
      <button className="store-card__head" onClick={() => setShop(open ? null : m.slug)} aria-expanded={open} title={m.tagline}>
        <span className="store-card__idx">M{index + 1}</span>
        <span className="store-card__logo"><img src={m.logo} alt="" onError={e => { (e.currentTarget as HTMLImageElement).style.visibility = 'hidden' }} /></span>
        <span className="store-card__title">
          <span className="store-card__name">{m.name}</span>
          {ig && <span className="store-card__ig">{ig}</span>}
        </span>
        <span className="store-card__browse">{open ? 'Close' : 'Browse'}</span>
      </button>
      <div className="store-card__rows">
        {slots.map(s => <SlotRow key={s} slot={s} products={products.filter(p => p.slot === s)} onOpen={() => setShop(m.slug)} />)}
      </div>
    </section>
  )
}

function SlotRow({ slot, products, onOpen }: { slot: Slot; products: Product[]; onOpen: () => void }) {
  const look = useStore(s => s.look)
  const notes = useStore(s => s.notes)
  const equip = useStore(s => s.equip)
  const clear = useStore(s => s.clear)
  const worn = products.find(p => look[slot] === p.sku)
  const idx = worn ? products.indexOf(worn) : -1
  const step = (d: number) => {
    if (!products.length) return
    const n = idx < 0 ? (d > 0 ? 0 : products.length - 1) : (idx + d + products.length) % products.length
    equip(products[n].sku)
  }
  const optional = !REQUIRED.includes(slot)
  return (
    <div className={'slot-row' + (worn ? '' : ' is-empty')}>
      <button className="slot-row__arrow" onClick={() => step(-1)} aria-label={`Previous ${SLOT_LABEL[slot]}`}>‹</button>
      <button className="slot-row__piece" onClick={onOpen}>
        <span className="slot-row__img">{(worn ?? products[0]) && <img key={(worn ?? products[0]).sku} src={(worn ?? products[0]).image} alt="" />}</span>
        <span className="slot-row__body">
          <span className="slot-row__slot">{SLOT_LABEL[slot]}{worn ? ` · ${idx + 1}/${products.length}` : ''}</span>
          {worn ? <>
            <span className="slot-row__name">{worn.name}</span>
            <span className="tags">{thriftTags(worn).map(t => <span key={t} className={'tag' + (t === '1 OF 1' ? ' tag--one' : '')}>{t}</span>)}</span>
            {notes[worn.sku] && <span className="slot-row__note">{notes[worn.sku]}</span>}
          </> : <span className="slot-row__name dim">Add a {SLOT_LABEL[slot].toLowerCase()}</span>}
        </span>
      </button>
      <button className="slot-row__arrow" onClick={() => step(1)} aria-label={`Next ${SLOT_LABEL[slot]}`}>›</button>
      {optional && worn && <button className="slot-row__clear" onClick={() => clear(slot)} aria-label={`Remove ${worn.name}`}>×</button>}
    </div>
  )
}
