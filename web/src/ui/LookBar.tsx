import { useState } from 'react'
import { bagUrl, inr, lookProducts, postAddLook } from '../lib/bag'
import { lookTitle, useStore } from '../store'

/** Look summary and Lock the look (url-contract: HOST + cartPath ?add=SKU,SKU&look=TITLE, target _parent, plus postMessage). */
export function LookBar() {
  const catalog = useStore(s => s.catalog)
  const look = useStore(s => s.look)
  const storedTitle = useStore(s => s.title)
  const stageNotes = useStore(s => s.stageNotes)
  const title = lookTitle(look, storedTitle)
  const items = lookProducts(look, catalog)
  const skus = items.map(p => p.sku)
  const total = items.reduce((a, p) => a + p.price, 0)
  const merchants = new Set(items.map(p => p.merchant)).size
  const url = bagUrl(skus, title)
  const [locked, setLocked] = useState<string | null>(null)
  const isLocked = locked === skus.join(',')

  return (
    <div className="look-bar" aria-label="Your look">
      <div className="look-bar__summary">
        <div className="look-bar__title">{title}</div>
        <div className="look-bar__meta"><span className="mono">{items.length} pieces · {merchants} stores</span> <strong className="mono">{inr(total)}</strong></div>
        {isLocked && !url && <div className="look-bar__locked">Locked: {skus.join(' · ')}. One checkout on Bluehost.</div>}
        {!isLocked && stageNotes && <div className="look-bar__notes">{stageNotes}</div>}
      </div>
      {url ? (
        <a className="btn btn--primary btn--lock" href={url} target="_parent" onClick={() => postAddLook(skus, title)}>Lock the look</a>
      ) : (
        <button className="btn btn--primary btn--lock" onClick={() => { postAddLook(skus, title); setLocked(skus.join(',')) }}>{isLocked ? 'Look locked ✓' : 'Lock the look'}</button>
      )}
    </div>
  )
}
