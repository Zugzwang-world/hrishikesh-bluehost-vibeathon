import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { bagFromUrl, getBag, groupByStore, inr, removeFromBag, thriftTag, useCatalog, useLive, type StoreGroup } from './data'
import { Link, StoreLogo, nav } from './nav'

function StoreCard({ g }: { g: StoreGroup }) {
  const m = g.merchant
  return (
    <motion.article layout className="s-store" style={{ ['--brand' as string]: m.brandColor, ['--brand-accent' as string]: m.accentColor }}
      initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ type: 'spring', stiffness: 380, damping: 32 }}>
      <header className="s-store__head">
        <StoreLogo slug={m.slug} name={m.name} />
        <div className="s-store__id">
          <span className="s-store__name">{m.name}</span>
          <a className="s-store__ig" href={`https://instagram.com/${m.instagram.replace('@', '')}`} target="_blank" rel="noreferrer">{m.instagram}</a>
        </div>
      </header>
      <ul className="s-items">
        <AnimatePresence initial={false}>
          {g.items.map(p => (
            <motion.li key={p.sku} className="s-item" layout exit={{ opacity: 0, x: -16 }} transition={{ duration: 0.18 }}>
              <img className="s-item__img" src={p.image} alt="" loading="lazy" />
              <div className="s-item__body">
                <span className="s-item__name">{p.name}</span>
                <span className="s-tag">{thriftTag(p)}</span>
              </div>
              <span className="s-price">{inr(p.price)}</span>
              <button className="s-item__x" aria-label={`Remove ${p.name}`} onClick={() => removeFromBag(p.sku)}>×</button>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      <footer className="s-store__foot"><span>Store subtotal</span><span className="s-price">{inr(g.subtotal)}</span></footer>
    </motion.article>
  )
}

export default function BagPage({ add, look }: { add: string | null; look: string | null }) {
  useLive()
  const catalog = useCatalog()
  const consumed = useRef(false)
  useEffect(() => {
    if (!catalog || consumed.current || add === null) return
    consumed.current = true
    bagFromUrl(catalog, add, look)
    nav('/bag', true) // keep the bag editable on reload
  }, [catalog, add, look])

  if (!catalog || (add !== null && !consumed.current)) return <main className="s-page"><p className="s-loading">Opening your bag…</p></main>

  const bag = getBag()
  const groups = groupByStore(catalog, bag.skus)
  const skus = groups.flatMap(g => g.items.map(p => p.sku))
  const total = groups.reduce((a, g) => a + g.subtotal, 0)
  const half = Math.ceil(groups.length / 2)
  const title = bag.look || 'Your look'

  if (!skus.length) {
    return (
      <main className="s-page s-empty">
        <p className="s-eyebrow">SHOP-UNI-FY · BAG</p>
        <h1 className="s-hero">Your bag is empty</h1>
        <p className="s-serif">Style a look on the stage, then lock it in.</p>
        <a className="s-btn s-btn--primary" href="/">Back to the stage</a>
      </main>
    )
  }

  return (
    <main className="s-page">
      <p className="s-eyebrow">LOOK LOCKED · ONE BAG · {groups.length} {groups.length === 1 ? 'STORE' : 'STORES'}</p>
      <h1 className="s-hero">{title}</h1>
      <p className="s-serif">One look, {groups.length} independent {groups.length === 1 ? 'store' : 'stores'}, one checkout.</p>

      <div className="s-bag">
        <div className="s-bag__stage">
          <iframe key={skus.join(',')} title="Your locked look on the stage" src={`/?embed=1&mode=locked&look=${skus.join(',')}`} loading="eager" />
        </div>
        <div className="s-bag__col s-bag__col--l">
          <AnimatePresence>{groups.slice(0, half).map(g => <StoreCard key={g.merchant.slug} g={g} />)}</AnimatePresence>
        </div>
        <div className="s-bag__col s-bag__col--r">
          <AnimatePresence>{groups.slice(half).map(g => <StoreCard key={g.merchant.slug} g={g} />)}</AnimatePresence>
        </div>
      </div>

      <section className="s-sum">
        <div className="s-sum__total">
          <span className="s-label">Total across stores</span>
          <span className="s-sum__amt">{inr(total)}</span>
          <span className="s-label">{skus.length} {skus.length === 1 ? 'piece' : 'pieces'} · {groups.length} {groups.length === 1 ? 'store' : 'stores'} · every piece 1 of 1</span>
        </div>
        <div className="s-sum__actions">
          <a className="s-btn s-btn--ghost" href={`/?look=${skus.join(',')}`}>Back to the stage</a>
          <Link className="s-btn s-btn--primary s-btn--lg" to="/checkout">Checkout</Link>
        </div>
      </section>
    </main>
  )
}
