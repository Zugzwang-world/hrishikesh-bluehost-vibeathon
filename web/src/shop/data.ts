// Fallback shop data layer: catalog fetch + localStorage (demo only, no backend).
import { useEffect, useState } from 'react'
import type { Catalog, Merchant, Product } from '../api/types'

export type Status = 'New' | 'Packed' | 'Shipped' | 'Delivered'
export const STATUSES: Status[] = ['New', 'Packed', 'Shipped', 'Delivered']
export type Line = { sku: string; name: string; price: number; image: string; size: string; condition: string; era: string }
export type SubOrder = { merchant: string; status: Status; items: Line[]; subtotal: number; history: { status: Status; at: number }[] }
export type Order = {
  number: string; createdAt: number; look: string
  customer: { name: string; email: string; phone: string }
  address: { line1: string; line2: string; city: string; pin: string }
  speed: 'standard' | 'express'; shipping: number; payment: 'upi' | 'cod'
  subs: SubOrder[]; total: number; sample?: boolean
}
export type Bag = { skus: string[]; look: string }

const K_BAG = 'suf-bag'
const K_ORDERS = 'suf-orders'
const K_SAMPLES = 'suf-samples'
const EVT = 'suf-change'

export const inr = (n: number) => '₹' + Math.round(n).toLocaleString('en-IN')
export const thriftTag = (p: { size: string; condition: string; era: string }) =>
  ['1 OF 1', p.size, p.condition, p.era].filter(Boolean).join(' · ')

function read<T>(k: string, fallback: T): T {
  try { const s = localStorage.getItem(k); return s ? (JSON.parse(s) as T) : fallback } catch { return fallback }
}
function write(k: string, v: unknown) {
  try { localStorage.setItem(k, JSON.stringify(v)) } catch { /* private mode: in-memory only */ }
  window.dispatchEvent(new Event(EVT))
}

/* ---------- catalog ---------- */
let catalogPromise: Promise<Catalog> | null = null
let catalogCache: Catalog | null = null
export function loadCatalog(): Promise<Catalog> {
  if (!catalogPromise) {
    catalogPromise = fetch('/catalog/catalog.json').then(r => r.json()).then((c: Catalog) => { catalogCache = c; return c })
    catalogPromise.catch(() => { catalogPromise = null })
  }
  return catalogPromise
}
export function useCatalog(): Catalog | null {
  const [c, setC] = useState<Catalog | null>(catalogCache)
  useEffect(() => { let on = true; loadCatalog().then(x => { if (on) setC(x) }).catch(() => {}); return () => { on = false } }, [])
  return c
}
export const productBy = (c: Catalog, sku: string) => c.products.find(p => p.sku === sku)
export const merchantBy = (c: Catalog, slug: string) => c.merchants.find(m => m.slug === slug)

/** Re-render on any shop data change: same tab, other tabs (storage event) and a 2 s poll. */
export function useLive() {
  const [, setN] = useState(0)
  useEffect(() => {
    const bump = () => setN(n => n + 1)
    window.addEventListener(EVT, bump)
    window.addEventListener('storage', bump)
    const t = window.setInterval(bump, 2000)
    return () => { window.removeEventListener(EVT, bump); window.removeEventListener('storage', bump); window.clearInterval(t) }
  }, [])
}

/* ---------- bag ---------- */
export const getBag = (): Bag => {
  const b = read<Bag>(K_BAG, { skus: [], look: '' })
  return { skus: Array.isArray(b.skus) ? b.skus : [], look: typeof b.look === 'string' ? b.look : '' }
}
export const setBag = (b: Bag) => write(K_BAG, b)
export function bagFromUrl(c: Catalog, add: string, look: string | null) {
  const seen = new Set<string>()
  const skus: string[] = []
  for (const raw of add.split(',')) {
    const sku = raw.trim().toUpperCase()
    if (!sku || seen.has(sku) || !productBy(c, sku)) continue
    seen.add(sku); skus.push(sku)
  }
  setBag({ skus, look: (look ?? '').trim() || 'Your look' })
}
export function removeFromBag(sku: string) { const b = getBag(); setBag({ ...b, skus: b.skus.filter(s => s !== sku) }) }

export type StoreGroup = { merchant: Merchant; items: Product[]; subtotal: number }
export function groupByStore(c: Catalog, skus: string[]): StoreGroup[] {
  const out: StoreGroup[] = []
  for (const m of c.merchants) {
    const items = skus.map(s => productBy(c, s)).filter((p): p is Product => !!p && p.merchant === m.slug)
    if (items.length) out.push({ merchant: m, items, subtotal: items.reduce((a, p) => a + p.price, 0) })
  }
  return out
}

/* ---------- orders ---------- */
export const getOrders = (): Order[] => read<Order[]>(K_ORDERS, [])
const getSamples = (): Order[] => read<Order[]>(K_SAMPLES, [])
export const findOrder = (num: string): Order | undefined =>
  [...getOrders(), ...getSamples()].find(o => o.number.toUpperCase() === num.toUpperCase())

function nextNumber(): string {
  let max = 1000
  for (const o of getOrders()) { const n = parseInt(o.number.replace(/\D/g, ''), 10); if (n > max) max = n }
  return 'SUF-' + (max + 1)
}
const line = (p: Product): Line => ({ sku: p.sku, name: p.name, price: p.price, image: p.image, size: p.size, condition: p.condition, era: p.era })

export function placeOrder(c: Catalog, bag: Bag, form: Pick<Order, 'customer' | 'address' | 'speed' | 'payment'>): Order {
  const now = Date.now()
  const groups = groupByStore(c, bag.skus)
  const shipping = form.speed === 'express' ? 99 : 0
  const subs: SubOrder[] = groups.map(g => ({
    merchant: g.merchant.slug, status: 'New', items: g.items.map(line), subtotal: g.subtotal, history: [{ status: 'New', at: now }],
  }))
  const order: Order = {
    number: nextNumber(), createdAt: now, look: bag.look || 'Your look', ...form, shipping, subs,
    total: subs.reduce((a, s) => a + s.subtotal, 0) + shipping,
  }
  write(K_ORDERS, [order, ...getOrders()])
  setBag({ skus: [], look: '' }) // demo mode: pieces stay available in the catalog
  return order
}

export function setStatus(num: string, slug: string, status: Status) {
  const apply = (list: Order[]) => {
    let hit = false
    const next = list.map(o => {
      if (o.number !== num) return o
      hit = true
      return {
        ...o, subs: o.subs.map(s => {
          if (s.merchant !== slug || s.status === status) return s
          const idx = STATUSES.indexOf(status)
          return { ...s, status, history: [...s.history.filter(h => STATUSES.indexOf(h.status) < idx), { status, at: Date.now() }] }
        }),
      }
    })
    return hit ? next : null
  }
  const a = apply(getOrders())
  if (a) { write(K_ORDERS, a); return }
  const b = apply(getSamples())
  if (b) write(K_SAMPLES, b)
}

export function overallStatus(o: Order): Status {
  let min = 3
  for (const s of o.subs) min = Math.min(min, STATUSES.indexOf(s.status))
  return STATUSES[Math.max(0, min)]
}

/* ---------- merchant samples (two past orders per store, marked Sample) ---------- */
const SAMPLE_PEOPLE = ['Ananya Rao', 'Kabir Shetty', 'Meera Iyer', 'Rohan Menon', 'Tara D\'Souza', 'Vikram Nair', 'Isha Kulkarni', 'Arjun Reddy', 'Zoya Khan', 'Dev Bhat']
export function ensureSamples(c: Catalog) {
  const have = getSamples()
  if (have.length) return
  const DAY = 86400000
  const now = Date.now()
  const out: Order[] = []
  c.merchants.forEach((m, mi) => {
    const prods = c.products.filter(p => p.merchant === m.slug)
    ;[0, 1].forEach(k => {
      const pick = prods.slice(2 + k * 2, 2 + k * 2 + (k === 0 ? 2 : 1))
      const items = (pick.length ? pick : prods.slice(0, 1)).map(line)
      const subtotal = items.reduce((a, l) => a + l.price, 0)
      const at = now - (k === 0 ? 6 : 2) * DAY - mi * 3600000
      const status: Status = k === 0 ? 'Delivered' : 'Shipped'
      const history = STATUSES.slice(0, STATUSES.indexOf(status) + 1).map((s, i) => ({ status: s, at: at + i * DAY * 0.6 }))
      out.push({
        number: 'SUF-0' + (941 + mi * 2 + k), createdAt: at, look: 'Sample order',
        customer: { name: SAMPLE_PEOPLE[(mi * 2 + k) % SAMPLE_PEOPLE.length], email: '', phone: '' },
        address: { line1: '', line2: '', city: 'Bengaluru', pin: '5600' + (10 + mi * 7 + k) },
        speed: 'standard', shipping: 0, payment: k ? 'cod' : 'upi',
        subs: [{ merchant: m.slug, status, items, subtotal, history }], total: subtotal, sample: true,
      })
    })
  })
  write(K_SAMPLES, out)
}
export function merchantOrders(slug: string): Order[] {
  return [...getOrders(), ...getSamples()].filter(o => o.subs.some(s => s.merchant === slug)).sort((a, b) => b.createdAt - a.createdAt)
}

export const when = (t: number) =>
  new Date(t).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
