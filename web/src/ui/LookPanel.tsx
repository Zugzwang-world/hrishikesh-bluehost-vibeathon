import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { REQUIRED, SLOTS } from '../config'
import { bagUrl, inr, lookProducts, postAddLook } from '../lib/bag'
import { OCCASION_LABEL, productBySku, useStore } from '../store'

const SLOT_LABEL: Record<string, string> = { top: 'Top', outerwear: 'Layer', bottom: 'Bottom', footwear: 'Shoes', headwear: 'Head', eyewear: 'Eyes', watch: 'Wrist', neckwear: 'Neck' }

/** Items, merchants, prices, total, Add look to bag (url-contract). Bottom sheet on phones. */
export function LookPanel() {
  const catalog = useStore(s => s.catalog)
  const look = useStore(s => s.look)
  const title = useStore(s => s.title)
  const notes = useStore(s => s.notes)
  const stageNotes = useStore(s => s.stageNotes)
  const occasion = useStore(s => s.occasion)
  const clear = useStore(s => s.clear)
  const setShop = useStore(s => s.setShop)
  const sheetOpen = useStore(s => s.sheetOpen)
  const set = useStore(s => s.set)
  const items = lookProducts(look, catalog)
  const skus = items.map(p => p.sku)
  const total = items.reduce((a, p) => a + p.price, 0)
  const merchants = new Set(items.map(p => p.merchant)).size
  const url = bagUrl(skus, title)
  const [added, setAdded] = useState<string | null>(null)

  return (
    <aside className={'look-panel' + (sheetOpen ? ' is-open' : '')} aria-label="Your look">
      <button className="look-panel__handle" onClick={() => set({ sheetOpen: !sheetOpen })} aria-expanded={sheetOpen}>
        <span className="look-panel__grip" />
        <span>{items.length} items · {merchants} merchants · {inr(total)}</span>
      </button>
      <div className="look-panel__head">
        <div className="eyebrow">{occasion ? OCCASION_LABEL : 'Fitting room'}</div>
        <h2 className="look-panel__title">{title}</h2>
      </div>
      <ul className="look-list">
        <AnimatePresence initial={false}>
          {SLOTS.map(s => {
            const p = productBySku(catalog, look[s])
            if (!p) {
              if (REQUIRED.includes(s)) return null
              return null
            }
            const m = catalog?.merchants.find(x => x.slug === p.merchant)
            return (
              <motion.li key={p.sku} className="look-item" layout
                initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}>
                <button className="look-item__img" onClick={() => m && setShop(m.slug)} aria-label={`Open ${m?.name}`}><img src={p.image} alt="" /></button>
                <div className="look-item__body">
                  <div className="look-item__slot">{SLOT_LABEL[s]}</div>
                  <div className="look-item__name">{p.name} <span className="dim">· {p.colorName}</span></div>
                  <div className="look-item__merchant"><span className="dot" style={{ background: m?.brandColor }} />{m?.name}</div>
                  {notes[p.sku] && <div className="look-item__note">{notes[p.sku]}</div>}
                </div>
                <div className="look-item__price">
                  {inr(p.price)}
                  {!REQUIRED.includes(s) && <button className="icon-btn" onClick={() => clear(s)} aria-label={`Remove ${p.name}`}>×</button>}
                </div>
              </motion.li>
            )
          })}
        </AnimatePresence>
      </ul>
      {stageNotes && <p className="look-panel__stage-notes">{stageNotes}</p>}
      <div className="look-panel__foot">
        <div className="look-total">
          <span>{items.length} items · {merchants} merchants</span>
          <strong>{inr(total)}</strong>
        </div>
        {url ? (
          <a className="btn btn--primary btn--block" href={url} target="_top" onClick={() => postAddLook(skus, title)}>Add look to bag</a>
        ) : (
          <div className="bag-summary" role="status">
            {added === skus.join(',')
              ? <div className="bag-summary__done"><strong>In your bag</strong> {items.length} pieces from {merchants} merchants, {inr(total)}. One checkout on Bluehost.<span className="bag-summary__skus">{skus.join(' · ')}</span></div>
              : null}
            <button className="btn btn--primary btn--block" onClick={() => { postAddLook(skus, title); setAdded(skus.join(',')) }}>{added === skus.join(',') ? 'Added to bag ✓' : 'Add look to bag'}</button>
          </div>
        )}
      </div>
    </aside>
  )
}
