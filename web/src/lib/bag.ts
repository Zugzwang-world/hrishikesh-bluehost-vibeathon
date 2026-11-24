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
  return `${PARAMS.host}/cart?add=${skus.join(',')}&look=${encodeURIComponent(title)}`
}

export function postAddLook(skus: string[], title: string) {
  try { window.parent.postMessage({ type: 'ensemble:add-look', skus, look: title }, '*') } catch { /* ignore */ }
}

export const inr = (n: number) => '₹' + n.toLocaleString('en-IN')
