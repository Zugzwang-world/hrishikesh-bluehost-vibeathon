import { create } from 'zustand'
import { DEFAULT_LOOK, REQUIRED, SLOTS, type Slot } from './config'
import type { Catalog, Look, Product, StageCheckResult } from './api/types'
import { PARAMS } from './lib/params'

export type Mode = 'fit' | 'show'
export const KEYNOTE = 'keynote'
export const OCCASION_LABEL = 'On stage · Bluehost Bangalore'
export const DEFAULT_TITLE = 'Hrishikesh on stage'

type State = {
  catalog: Catalog | null
  look: Look
  shop: string | null
  mode: Mode
  showStart: number
  occasion: string | null
  title: string
  notes: Record<string, string>
  stageNotes: string
  thinking: boolean
  check: StageCheckResult | null
  checkVisible: boolean
  sheetOpen: boolean
  setCatalog: (c: Catalog) => void
  equip: (sku: string) => void
  clear: (slot: Slot) => void
  setShop: (slug: string | null) => void
  applyLook: (look: Partial<Record<Slot, string | null>>, stagger?: number) => void
  surprise: () => void
  setMode: (m: Mode) => void
  set: (p: Partial<State>) => void
}

const timers: number[] = []
const cancelStagger = () => { while (timers.length) clearTimeout(timers.pop()) }

export const productBySku = (c: Catalog | null, sku: string | null | undefined): Product | undefined =>
  sku && c ? c.products.find(p => p.sku === sku) : undefined

export const useStore = create<State>((set, get) => ({
  catalog: null,
  look: {},
  shop: null,
  mode: 'fit',
  showStart: 0,
  occasion: PARAMS.event === KEYNOTE ? KEYNOTE : null,
  title: DEFAULT_TITLE,
  notes: {},
  stageNotes: '',
  thinking: false,
  check: null,
  checkVisible: false,
  sheetOpen: false,

  setCatalog: c => {
    const look: Look = {}
    const skus = [...(PARAMS.look ?? DEFAULT_LOOK), ...(PARAMS.try ? [PARAMS.try] : [])]
    for (const s of skus) { const p = c.products.find(x => x.sku === s); if (p) look[p.slot] = p.sku }
    // never leave a required slot empty
    for (const s of REQUIRED) if (!look[s]) { const d = DEFAULT_LOOK.map(k => c.products.find(p => p.sku === k)).find(p => p?.slot === s); if (d) look[s] = d.sku }
    const t = productBySku(c, PARAMS.try)
    set({ catalog: c, look, shop: t ? t.merchant : (c.merchants[0]?.slug ?? null) })
  },

  equip: sku => {
    const p = productBySku(get().catalog, sku)
    if (!p) return
    cancelStagger()
    set(s => ({ look: { ...s.look, [p.slot]: sku }, check: null }))
  },

  clear: slot => {
    if (REQUIRED.includes(slot)) return
    cancelStagger()
    set(s => ({ look: { ...s.look, [slot]: null }, check: null }))
  },

  setShop: slug => set({ shop: slug }),

  applyLook: (target, stagger = 260) => {
    cancelStagger()
    const c = get().catalog
    let i = 0
    for (const s of SLOTS) {
      if (!(s in target)) continue
      const sku = target[s] ?? null
      if (sku && !productBySku(c, sku)) continue
      if (REQUIRED.includes(s) && !sku) continue
      if ((get().look[s] ?? null) === sku) continue
      const apply = () => set(st => ({ look: { ...st.look, [s]: sku }, check: null }))
      if (stagger <= 0) apply()
      else timers.push(window.setTimeout(apply, stagger * i++))
    }
  },

  surprise: () => {
    const c = get().catalog
    if (!c) return
    const pick = (s: Slot) => { const ps = c.products.filter(p => p.slot === s); return ps[Math.floor(Math.random() * ps.length)]?.sku ?? null }
    const look: Partial<Record<Slot, string | null>> = {}
    for (const s of SLOTS) look[s] = REQUIRED.includes(s) || Math.random() < (s === 'outerwear' ? 0.6 : 0.4) ? pick(s) : null
    set({ notes: {}, title: DEFAULT_TITLE })
    get().applyLook(look, 140)
  },

  setMode: m => set({ mode: m, showStart: performance.now(), checkVisible: false, ...(m === 'fit' ? {} : { check: null }) }),
  set: p => set(p),
}))
