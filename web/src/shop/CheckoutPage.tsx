import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { getBag, groupByStore, inr, merchantBy, placeOrder, useCatalog, useLive, type Order } from './data'
import { Chip, Link, StoreLogo } from './nav'

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="s-field">
      <span className="s-field__label">{label}{hint ? <em> {hint}</em> : null}</span>
      {children}
    </label>
  )
}

function Choice<T extends string>({ name, value, current, onPick, title, note, price }: {
  name: string; value: T; current: T; onPick: (v: T) => void; title: string; note: string; price: string
}) {
  const on = value === current
  return (
    <label className={on ? 's-choice is-on' : 's-choice'}>
      <input type="radio" name={name} value={value} checked={on} onChange={() => onPick(value)} />
      <span className="s-choice__dot" aria-hidden />
      <span className="s-choice__body"><strong>{title}</strong><span>{note}</span></span>
      <span className="s-price">{price}</span>
    </label>
  )
}

export function Placed({ order }: { order: Order }) {
  const catalog = useCatalog()
  const n = order.subs.length
  return (
    <motion.div className="s-modal" role="dialog" aria-modal="true" aria-labelledby="placed-title"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.div className="s-modal__card"
        initial={{ opacity: 0, y: 40, scale: 0.92 }} animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 22 }}>
        <p className="s-eyebrow">ORDER {order.number} · PLACED</p>
        <h2 id="placed-title" className="s-modal__title">Look locked.</h2>
        <p className="s-serif s-modal__sub">1 checkout, {n} {n === 1 ? 'store' : 'stores'}.</p>
        <ul className="s-rows">
          {order.subs.map((s, i) => {
            const m = catalog ? merchantBy(catalog, s.merchant) : undefined
            const name = m?.name ?? s.merchant
            return (
              <motion.li key={s.merchant} className="s-row" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 + i * 0.06 }}>
                <StoreLogo slug={s.merchant} name={name} small />
                <div className="s-row__body">
                  <strong>{name}</strong>
                  <span className="s-label">{s.items.length} {s.items.length === 1 ? 'piece' : 'pieces'} · {inr(s.subtotal)}</span>
                </div>
                <Chip status={s.status} />
                <a className="s-row__link" href={`/store/${s.merchant}?order=${order.number}`} target="_blank" rel="noreferrer">Open in {name} app ↗</a>
              </motion.li>
            )
          })}
        </ul>
        <div className="s-modal__foot">
          <span className="s-label">Total paid (demo) <b className="s-price">{inr(order.total)}</b></span>
          <div className="s-modal__btns">
            <a className="s-btn s-btn--ghost" href="/">Back to the stage</a>
            <Link className="s-btn s-btn--primary" to={`/orders/${order.number}`}>Track my order</Link>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function CheckoutPage() {
  useLive()
  const catalog = useCatalog()
  const [name, setName] = useState('Hrishikesh Hundekari')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [line1, setLine1] = useState('Green Room, Small Business AI Builder Tour')
  const [line2, setLine2] = useState('MG Road')
  const [city, setCity] = useState('Bengaluru')
  const [pin, setPin] = useState('560001')
  const [speed, setSpeed] = useState<'standard' | 'express'>('standard')
  const [payment, setPayment] = useState<'upi' | 'cod'>('upi')
  const [placed, setPlaced] = useState<Order | null>(null)
  const [busy, setBusy] = useState(false)

  if (!catalog) return <main className="s-page"><p className="s-loading">Loading checkout…</p></main>
  const bag = getBag()
  const groups = groupByStore(catalog, bag.skus)
  const sub = groups.reduce((a, g) => a + g.subtotal, 0)
  const ship = speed === 'express' ? 99 : 0
  const count = groups.reduce((a, g) => a + g.items.length, 0)

  const submit = () => {
    if (!groups.length || busy) return
    setBusy(true)
    const o = placeOrder(catalog, bag, {
      customer: { name: name.trim() || 'Guest', email: email.trim(), phone: phone.trim() },
      address: { line1, line2, city, pin }, speed, payment,
    })
    window.setTimeout(() => { setPlaced(o); setBusy(false) }, 450)
  }

  return (
    <main className="s-page">
      <div className="s-co__head">
        <div>
          <p className="s-eyebrow">{bag.look ? bag.look.toUpperCase() + ' · ' : ''}{count} PIECES · {groups.length} STORES</p>
          <h1 className="s-hero s-hero--md">Checkout</h1>
        </div>
        <span className="s-demo">DEMO · NO REAL PAYMENT</span>
      </div>

      {!groups.length && !placed ? (
        <div className="s-empty">
          <p className="s-serif">Nothing to check out yet.</p>
          <div className="s-modal__btns"><Link className="s-btn s-btn--ghost" to="/orders">My orders</Link><a className="s-btn s-btn--primary" href="/">Back to the stage</a></div>
        </div>
      ) : (
        <form className="s-co" onSubmit={e => { e.preventDefault(); submit() }}>
          <div className="s-co__form">
            <section className="s-panel">
              <h2 className="s-h2">Contact</h2>
              <Field label="Full name"><input value={name} onChange={e => setName(e.target.value)} autoComplete="name" /></Field>
              <div className="s-grid2">
                <Field label="Email" hint="optional"><input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" /></Field>
                <Field label="Phone" hint="optional"><input type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+91" autoComplete="tel" /></Field>
              </div>
            </section>
            <section className="s-panel">
              <h2 className="s-h2">Delivery address</h2>
              <Field label="Address line 1"><input value={line1} onChange={e => setLine1(e.target.value)} /></Field>
              <Field label="Address line 2"><input value={line2} onChange={e => setLine2(e.target.value)} /></Field>
              <div className="s-grid2">
                <Field label="City"><input value={city} onChange={e => setCity(e.target.value)} /></Field>
                <Field label="PIN code"><input value={pin} onChange={e => setPin(e.target.value)} inputMode="numeric" /></Field>
              </div>
            </section>
            <section className="s-panel">
              <h2 className="s-h2">Delivery speed</h2>
              <Choice name="speed" value="standard" current={speed} onPick={setSpeed} title="Standard" note="4–6 days · each store ships its pieces" price="Free" />
              <Choice name="speed" value="express" current={speed} onPick={setSpeed} title="Express" note="1–2 days in Bengaluru" price={inr(99)} />
            </section>
            <section className="s-panel">
              <h2 className="s-h2">Payment <span className="s-demo s-demo--sm">DEMO</span></h2>
              <Choice name="pay" value="upi" current={payment} onPick={setPayment} title="UPI" note="Demo only, no money moves" price="" />
              <Choice name="pay" value="cod" current={payment} onPick={setPayment} title="Cash on delivery" note="Pay each store when it arrives" price="" />
            </section>
          </div>

          <aside className="s-co__sum s-panel">
            <h2 className="s-h2">Your look</h2>
            {groups.map(g => (
              <div key={g.merchant.slug} className="s-co__store">
                <div className="s-co__storehead"><StoreLogo slug={g.merchant.slug} name={g.merchant.name} small /><span className="s-price">{inr(g.subtotal)}</span></div>
                <div className="s-co__thumbs">
                  {g.items.map(p => <img key={p.sku} src={p.image} alt={p.name} title={p.name} loading="lazy" />)}
                </div>
              </div>
            ))}
            <dl className="s-co__lines">
              <div><dt>Pieces</dt><dd className="s-price">{inr(sub)}</dd></div>
              <div><dt>Delivery</dt><dd className="s-price">{ship ? inr(ship) : 'Free'}</dd></div>
              <div className="s-co__total"><dt>Total</dt><dd>{inr(sub + ship)}</dd></div>
            </dl>
            <button type="submit" className="s-btn s-btn--primary s-btn--lg s-btn--block" disabled={busy || !groups.length}>
              {busy ? 'Placing order…' : `Place order · ${inr(sub + ship)}`}
            </button>
            <p className="s-fine">Demo checkout. One SHOP-UNI-FY order, split into one order per store. Pieces stay available.</p>
          </aside>
        </form>
      )}

      <AnimatePresence>{placed ? <Placed order={placed} /> : null}</AnimatePresence>
    </main>
  )
}
