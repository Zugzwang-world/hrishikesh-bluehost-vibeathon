import { motion } from 'motion/react'
import { STATUSES, findOrder, getOrders, inr, merchantBy, overallStatus, thriftTag, useCatalog, useLive, when, type SubOrder } from './data'
import { Chip, Link, StoreLogo } from './nav'

const STEP_NOTE: Record<string, string> = {
  New: 'Order received by the store',
  Packed: 'Washed, pressed, tagged 1 of 1',
  Shipped: 'On its way to you',
  Delivered: 'At your door',
}

export function Timeline({ sub }: { sub: SubOrder }) {
  const cur = STATUSES.indexOf(sub.status)
  return (
    <ol className="s-tl">
      {STATUSES.map((st, i) => {
        const h = sub.history.find(x => x.status === st)
        const done = i <= cur
        return (
          <li key={st} className={done ? (i === cur ? 's-tl__step is-cur' : 's-tl__step is-done') : 's-tl__step'}>
            <motion.span className="s-tl__dot" animate={{ scale: i === cur ? [1, 1.35, 1] : 1 }} transition={{ duration: 0.5 }} />
            <span className="s-tl__txt">
              <strong>{st}</strong>
              <span>{done && h ? when(h.at) : STEP_NOTE[st]}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export function OrderPage({ number }: { number: string }) {
  useLive()
  const catalog = useCatalog()
  const o = findOrder(number)
  if (!o) {
    return (
      <main className="s-page s-empty">
        <p className="s-eyebrow">ORDER {number.toUpperCase()}</p>
        <h1 className="s-hero s-hero--md">Not found</h1>
        <p className="s-serif">Orders live in this browser for the demo.</p>
        <Link className="s-btn s-btn--ghost" to="/orders">My orders</Link>
      </main>
    )
  }
  const overall = overallStatus(o)
  return (
    <main className="s-page">
      <p className="s-eyebrow">ORDER {o.number} · PLACED {when(o.createdAt).toUpperCase()}</p>
      <h1 className="s-hero s-hero--md">{o.look}</h1>
      <p className="s-serif">1 checkout, {o.subs.length} {o.subs.length === 1 ? 'store' : 'stores'}. Each store updates its own part live.</p>
      <div className="s-ord__meta">
        <span className="s-label">Overall</span><Chip status={overall} />
        <span className="s-label">{o.speed === 'express' ? 'Express' : 'Standard'} delivery · {o.payment === 'upi' ? 'UPI' : 'Cash on delivery'} · {inr(o.total)}</span>
        <span className="s-demo s-demo--sm">DEMO</span>
      </div>
      <div className="s-prog" aria-label="Delivery progress across stores">
        <div className="s-prog__bar"><motion.span initial={{ width: 0 }} animate={{ width: `${(o.subs.reduce((a, s) => a + STATUSES.indexOf(s.status), 0) / (3 * o.subs.length)) * 100}%` }} transition={{ type: 'spring', stiffness: 120, damping: 20 }} /></div>
        <span className="s-label">
          {(['Packed', 'Shipped', 'Delivered'] as const).map(st => `${o.subs.filter(s => STATUSES.indexOf(s.status) >= STATUSES.indexOf(st)).length} of ${o.subs.length} ${st.toLowerCase()}`).join(' · ')}
        </span>
      </div>
      <div className="s-ord">
        {o.subs.map(s => {
          const m = catalog ? merchantBy(catalog, s.merchant) : undefined
          const name = m?.name ?? s.merchant
          return (
            <motion.article key={s.merchant} className="s-panel s-ord__store" layout>
              <header className="s-ord__head">
                <StoreLogo slug={s.merchant} name={name} small />
                <div className="s-store__id"><span className="s-store__name">{name}</span><span className="s-store__ig">{m?.instagram}</span></div>
                <motion.span key={s.status} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 500, damping: 20 }}>
                  <Chip status={s.status} />
                </motion.span>
              </header>
              <Timeline sub={s} />
              <ul className="s-items s-items--compact">
                {s.items.map(p => (
                  <li key={p.sku} className="s-item">
                    <img className="s-item__img" src={p.image} alt="" loading="lazy" />
                    <div className="s-item__body"><span className="s-item__name">{p.name}</span><span className="s-tag">{thriftTag(p)}</span></div>
                    <span className="s-price">{inr(p.price)}</span>
                  </li>
                ))}
              </ul>
              <footer className="s-store__foot">
                <a className="s-row__link" href={`/store/${s.merchant}?order=${o.number}`} target="_blank" rel="noreferrer">Open in {name} app ↗</a>
                <span className="s-price">{inr(s.subtotal)}</span>
              </footer>
            </motion.article>
          )
        })}
      </div>
    </main>
  )
}

export function OrdersList() {
  useLive()
  const orders = getOrders()
  return (
    <main className="s-page">
      <p className="s-eyebrow">SHOP-UNI-FY · {orders.length} {orders.length === 1 ? 'ORDER' : 'ORDERS'}</p>
      <h1 className="s-hero s-hero--md">My orders</h1>
      {!orders.length ? (
        <div className="s-empty"><p className="s-serif">No orders yet. Lock a look on the stage first.</p><a className="s-btn s-btn--primary" href="/">Back to the stage</a></div>
      ) : (
        <ul className="s-olist">
          {orders.map(o => (
            <li key={o.number}>
              <Link className="s-olist__row s-panel" to={`/orders/${o.number}`}>
                <span className="s-olist__num">{o.number}</span>
                <span className="s-olist__look">{o.look}<span className="s-label">{when(o.createdAt)} · {o.subs.reduce((a, s) => a + s.items.length, 0)} pieces · {o.subs.length} stores</span></span>
                <span className="s-olist__logos">{o.subs.map(s => <StoreLogo key={s.merchant} slug={s.merchant} name={s.merchant} small />)}</span>
                <span className="s-price">{inr(o.total)}</span>
                <Chip status={overallStatus(o)} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
