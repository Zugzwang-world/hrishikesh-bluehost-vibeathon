import { bagUrl, inr, lookProducts, postAddLook, SELF_BAG } from '../lib/bag'
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

  return (
    <div className="look-bar" aria-label="Your look">
      <div className="look-bar__summary">
        <div className="look-bar__title">{title}</div>
        <div className="look-bar__meta"><span className="mono">{items.length} pieces · {merchants} stores</span> <strong className="mono">{inr(total)}</strong></div>
        {stageNotes && <div className="look-bar__notes">{stageNotes}</div>}
      </div>
      <a className="btn btn--primary btn--lock" href={url} target={SELF_BAG ? '_self' : '_parent'} onClick={() => postAddLook(skus, title)}>Lock the look</a>
    </div>
  )
}
