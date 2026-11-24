import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { STATUSES, ensureSamples, inr, merchantBy, merchantOrders, setStatus, thriftTag, useCatalog, useLive, when, type Order, type Status } from './data'
import { Chip, StoreLogo, nav } from './nav'
import { Timeline } from './OrdersPage'

function Drawer({ o, slug, onClose, onSet }: { o: Order; slug: string; onClose: () => void; onSet: (st: Status) => void }) {
  const s = o.subs.find(x => x.merchant === slug)!
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  const others = o.subs.length - 1
  return (
    <>
      <motion.div className="a-scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
      <motion.aside className="a-drawer" role="dialog" aria-modal="true" aria-label={`Order ${o.number}`}
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 380, damping: 38 }}>
        <header className="a-drawer__head">
          <div>
            <span className="a-mono">{o.number}</span>
            <h2>{o.customer.name}</h2>
            <span className="a-dim">{when(o.createdAt)}{o.sample ? '' : ' · via SHOP-UNI-FY Stage'}</span>
          </div>
          <button className="a-x" onClick={onClose} aria-label="Close" autoFocus>×</button>
        </header>
        <div className="a-drawer__body">
          <section>
            <h3>Status</h3>
            <div className="a-seg" role="group" aria-label="Order status">
              {STATUSES.map(st => (
                <button key={st} className={st === s.status ? 'is-on' : ''} aria-pressed={st === s.status} onClick={() => onSet(st)}>{st}</button>
              ))}
            </div>
            <Timeline sub={s} />
          </section>
          <section>
            <h3>{s.items.length} {s.items.length === 1 ? 'piece' : 'pieces'} from your store</h3>
            <ul className="a-items">
              {s.items.map(p => (
                <li key={p.sku}>
                  <img src={p.image} alt="" />
                  <div><strong>{p.name}</strong><span className="a-mono a-dim">{p.sku} · {thriftTag(p)}</span></div>
                  <span className="a-mono">{inr(p.price)}</span>
                </li>
              ))}
            </ul>
            <div className="a-line"><span>Subtotal</span><strong>{inr(s.subtotal)}</strong></div>
            {others > 0 ? <p className="a-note">Part of the look “{o.look}”: one checkout across {o.subs.length} stores. You only ship your {s.items.length === 1 ? 'piece' : 'pieces'}.</p> : null}
            {o.sample ? null : <a className="a-look" href={`/?look=${o.subs.flatMap(x => x.items.map(i => i.sku)).join(',')}`} target="_blank" rel="noreferrer">See the whole look on the Stage ↗</a>}
          </section>
          <section className="a-grid2">
            <div><h3>Customer</h3><p>{o.customer.name}<br /><span className="a-dim">{o.customer.email || 'No email (demo)'}<br />{o.customer.phone || 'No phone (demo)'}</span></p></div>
            <div><h3>Ship to</h3><p>{[o.address.line1, o.address.line2].filter(Boolean).join(', ') || 'On file'}<br />{o.address.city} {o.address.pin}</p></div>
            <div><h3>Delivery</h3><p>{o.speed === 'express' ? 'Express · 1–2 days' : 'Standard · 4–6 days'}</p></div>
            <div><h3>Payment</h3><p>{o.payment === 'upi' ? 'UPI (demo)' : 'Cash on delivery'}</p></div>
          </section>
        </div>
      </motion.aside>
    </>
  )
}

function StorePicker() {
  const catalog = useCatalog()
  return (
    <main className="a-pick">
      <h1>Store admin</h1>
      <p className="a-dim">Pick a store. Every SHOP-UNI-FY seller gets their own merchant app.</p>
      <ul>
        {catalog?.merchants.map(m => (
          <li key={m.slug}><a href={`/store/${m.slug}`} onClick={e => { e.preventDefault(); nav(`/store/${m.slug}`) }}><StoreLogo slug={m.slug} name={m.name} /><span>{m.name}<em className="a-dim">{m.instagram}</em></span></a></li>
        ))}
      </ul>
    </main>
  )
}

export default function MerchantApp({ slug, order }: { slug: string; order: string | null }) {
  useLive()
  const catalog = useCatalog()
  const [toast, setToast] = useState<string | null>(null)
  useEffect(() => { if (catalog) ensureSamples(catalog) }, [catalog])
  useEffect(() => { if (!toast) return; const t = window.setTimeout(() => setToast(null), 2600); return () => window.clearTimeout(t) }, [toast])
  if (!catalog) return <main className="a-pick"><p className="a-dim">Loading store…</p></main>
  const m = merchantBy(catalog, slug)
  if (!m) return <StorePicker />

  const orders = merchantOrders(slug)
  const mine = (o: Order) => o.subs.find(s => s.merchant === slug)!
  const revenue = orders.reduce((a, o) => a + mine(o).subtotal, 0)
  const live = catalog.products.filter(p => p.merchant === slug).length
  const toFulfil = orders.filter(o => ['New', 'Packed'].includes(mine(o).status)).length
  const open = order ? orders.find(o => o.number.toUpperCase() === order.toUpperCase()) : undefined
  const openOrder = (num: string | null) => nav(num ? `/store/${slug}?order=${num}` : `/store/${slug}`, true)
  const mark = (o: Order, st: Status) => {
    if (mine(o).status === st) return
    setStatus(o.number, slug, st)
    setToast(`${o.number} marked ${st}. Customer notified.`)
  }
  const advance = (o: Order) => {
    const cur = STATUSES.indexOf(mine(o).status)
    if (cur < 3) mark(o, STATUSES[cur + 1])
  }

  return (
    <div className="a-app" style={{ ['--brand' as string]: m.brandColor, ['--brand-accent' as string]: m.accentColor }}>
      <aside className="a-side">
        <div className="a-side__store">
          <StoreLogo slug={m.slug} name={m.name} />
          <span className="a-side__ig">{m.instagram}</span>
        </div>
        <nav className="a-side__nav">
          <span>Home</span><span className="is-on">Orders{toFulfil ? <b>{toFulfil}</b> : null}</span><span>Products</span><span>Customers</span><span>Analytics</span>
        </nav>
        <span className="a-side__foot">Powered by SHOP-UNI-FY</span>
      </aside>

      <main className="a-main">
        <header className="a-head">
          <div><h1>Orders</h1><span className="a-dim">{m.name} · {m.category}</span></div>
          <span className="a-demo">DEMO STORE</span>
        </header>
        <section className="a-kpis">
          <div className="a-kpi"><span>Orders</span><strong>{orders.length}</strong><em>{toFulfil} to fulfil</em></div>
          <div className="a-kpi"><span>Revenue</span><strong>{inr(revenue)}</strong><em>all time</em></div>
          <div className="a-kpi"><span>Pieces live</span><strong>{live}</strong><em>every piece 1 of 1</em></div>
        </section>
        <section className="a-card">
          <div className="a-table" role="table" aria-label="Orders">
            <div className="a-tr a-th" role="row">
              <span role="columnheader">Order</span><span role="columnheader">Customer</span><span role="columnheader">Pieces</span><span role="columnheader">Total</span><span role="columnheader">Status</span><span role="columnheader" />
            </div>
            <AnimatePresence initial={false}>
              {orders.map(o => {
                const s = mine(o)
                return (
                  <motion.div key={o.number} layout className={o.sample ? 'a-tr' : 'a-tr is-fresh'} role="row" tabIndex={0}
                    initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                    onClick={() => openOrder(o.number)} onKeyDown={e => { if (e.key === 'Enter') openOrder(o.number) }}>
                    <span role="cell" className="a-mono a-strong">{o.number}<em className="a-dim">{when(o.createdAt)}</em></span>
                    <span role="cell">{o.customer.name}</span>
                    <span role="cell" className="a-thumbs">{s.items.slice(0, 3).map(p => <img key={p.sku} src={p.image} alt="" />)}<em className="a-dim">{s.items.length}</em></span>
                    <span role="cell" className="a-mono">{inr(s.subtotal)}</span>
                    <span role="cell"><Chip status={s.status} sample={o.sample} /></span>
                    <span role="cell">
                      {s.status !== 'Delivered' ? (
                        <button className="a-next" onClick={e => { e.stopPropagation(); advance(o) }}>Mark {STATUSES[STATUSES.indexOf(s.status) + 1]}</button>
                      ) : <span className="a-dim">Done</span>}
                    </span>
                  </motion.div>
                )
              })}
            </AnimatePresence>
            {!orders.length ? <p className="a-dim a-emptyrow">No orders yet.</p> : null}
          </div>
        </section>
      </main>

      <AnimatePresence>{open ? <Drawer key={open.number} o={open} slug={slug} onClose={() => openOrder(null)} onSet={st => mark(open, st)} /> : null}</AnimatePresence>
      <AnimatePresence>{toast ? <motion.div className="a-toast" role="status" initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 30, opacity: 0 }}>{toast}</motion.div> : null}</AnimatePresence>
    </div>
  )
}
