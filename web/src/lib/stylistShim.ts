// Local stand-in for Lane D2's web/src/api/stylist.ts (same signatures). Never throws.
import { REQUIRED, SLOTS, type Slot } from '../config'
import type { Catalog, Look, Product, StageCheckResult, StageMetrics, StylistInput, StylistResult } from '../api/types'

function hexLum(hex: string) {
  const h = (hex || '#000000').replace('#', '')
  const c = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255).map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}
const contrast = (a: string, b: string) => { const x = hexLum(a), y = hexLum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) }

export async function askStylist(input: StylistInput, catalog: Catalog): Promise<StylistResult> {
  const words = input.prompt.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2)
  const score = (p: Product) => {
    const hay = [p.name, p.colorName, p.description, ...p.tags].join(' ').toLowerCase()
    return words.reduce((a, w) => a + (hay.includes(w) ? 1 : 0), 0)
  }
  const look = {} as Record<Slot, string | null>
  const notes: { sku: string; why: string }[] = []
  for (const s of SLOTS) {
    const cands = catalog.products.filter(p => p.slot === s).map(p => ({ p, sc: score(p) })).sort((a, b) => b.sc - a.sc)
    const best = cands[0]
    if (best && best.sc > 0) look[s] = best.p.sku
    else if (REQUIRED.includes(s)) look[s] = input.currentLook[s] ?? cands[0]?.p.sku ?? null
    else look[s] = input.currentLook[s] ?? null
    const sku = look[s]
    if (sku) {
      const p = catalog.products.find(x => x.sku === sku)
      const m = p && catalog.merchants.find(x => x.slug === p.merchant)
      if (p) notes.push({ sku, why: `${p.colorName} ${p.name.toLowerCase()} from ${m?.name ?? p.merchant} keeps the look sharp under lights.` })
    }
  }
  return { title: 'Hrishikesh on stage', look, notes, stageNotes: 'Mid-tone layers read well against a blue LED wall.', source: 'keywords' }
}

export function computeStageMetrics(look: Look, catalog: Catalog, ledWallColor: string): StageMetrics {
  const get = (s: Slot) => catalog.products.find(p => p.sku === look[s])
  const top = get('top'), outer = get('outerwear')
  const front = outer ?? top
  const items = SLOTS.map(get).filter(Boolean) as Product[]
  const print = items.find(p => p.material.printText)
  return {
    ledWallColor,
    topContrast: front ? contrast(front.material.color, ledWallColor) : 1,
    outerwearContrast: outer ? contrast(outer.material.color, ledWallColor) : null,
    brightnessUnderSpots: items.length ? items.reduce((a, p) => a + hexLum(p.material.color), 0) / items.length : 0,
    printReadability: print ? contrast(print.material.patternColor || '#000000', print.material.color) : null,
    merchants: new Set(items.map(p => p.merchant)).size,
    total: items.reduce((a, p) => a + p.price, 0),
  }
}

export async function stageCheck(look: Look, metrics: StageMetrics, catalog: Catalog): Promise<StageCheckResult> {
  const notes: string[] = []
  let score = 72
  if (metrics.topContrast >= 3) { score += 12; notes.push('Your top layer separates cleanly from the LED wall.') }
  else { score -= 10; notes.push('Your top layer blends into the LED wall; go lighter or warmer.') }
  if (metrics.brightnessUnderSpots > 0.6) { score -= 6; notes.push('Very bright pieces may clip under the spots.') }
  else { score += 8; notes.push('Tones sit well under the spotlights.') }
  notes.push(`${metrics.merchants} independent merchants in one look.`)
  let swap: StageCheckResult['swap'] = null
  const alt = metrics.topContrast < 3
    ? catalog.products.find(p => p.slot === 'outerwear' && p.sku !== look.outerwear && hexLum(p.material.color) > 0.05)
    : catalog.products.find(p => p.slot === 'watch' && p.sku !== look.watch)
  if (alt) swap = { slot: alt.slot, sku: alt.sku, why: `${alt.name} catches the light from row one.` }
  score = Math.max(0, Math.min(100, Math.round(score)))
  return { score, verdict: score >= 80 ? 'Stage ready' : 'Nearly there', notes: notes.slice(0, 3), swap, source: 'rules' }
}
