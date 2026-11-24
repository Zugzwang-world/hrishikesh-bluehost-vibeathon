import { REQUIRED, SLOTS, type Slot } from '../config'
import type { Catalog, Look, Product } from '../api/types'
import { PARAMS } from './params'

/** Required slots first, then optional, each in slot order (per url-contract). */
export const BAG_ORDER: Slot[] = [...REQUIRED, ...SLOTS.filter(s => !REQUIRED.includes(s))]

export function lookProducts(look: Look, catalog: Catalog | null): Product[] {
  if (!catalog) return []
  const out: Product[] = []
  for (const s of BAG_ORDER) {
    const sku = look[s]
    if (!sku) continue
    const p = catalog.products.find(x => x.sku === sku)
    if (p) out.push(p)
  }
  return out
}

export function bagUrl(skus: string[], title: string): string | null {
  if (!PARAMS.host) return null
  return `${PARAMS.host}${PARAMS.cartPath}?add=${skus.join(',')}&look=${encodeURIComponent(title)}`
}

export function postAddLook(skus: string[], title: string) {
  try { window.parent.postMessage({ type: 'ensemble:add-look', skus, look: title }, '*') } catch { /* ignore */ }
}

export const inr = (n: number) => '₹' + n.toLocaleString('en-IN')

/** Thrift fields (SHOP-UNI-FY catalog); optional so older catalogs still render. */
export type Thrift = { oneOfOne?: boolean; condition?: string; size?: string; era?: string }
export const thrift = (p: Product) => p as Product & Thrift
export function thriftTags(p: Product, withPrice = true): string[] {
  const t = thrift(p)
  const out: string[] = []
  if (t.oneOfOne) out.push('1 OF 1')
  if (t.condition) out.push(t.condition)
  if (t.size) out.push(t.size)
  if (t.era) out.push(t.era)
  if (withPrice) out.push(inr(p.price))
  return out
}
export const instagram = (m: { slug: string }) => (m as { instagram?: string }).instagram ?? null
