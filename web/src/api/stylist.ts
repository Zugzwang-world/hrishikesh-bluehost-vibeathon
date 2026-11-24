// Lane D2: AI stylist and stage check client. Dependency-free (fetch only).
// askStylist / stageCheck call the Vercel functions and never throw: on any failure they fall back to
// a local keyword matcher / rules engine. computeStageMetrics is pure code (WCAG contrast etc.).
import type { Catalog, Look, Product, StageCheckResult, StageMetrics, StylistInput, StylistResult } from './types'
import { DEFAULT_LOOK, REQUIRED, SLOTS, type Slot } from '../config'

const TIMEOUT_MS = 9000

// ---------- helpers ----------

type FullLook = Record<Slot, string | null>

function bySku(catalog: Catalog): Map<string, Product> {
  const m = new Map<string, Product>()
  for (const p of catalog?.products ?? []) m.set(p.sku, p)
  return m
}

function merchantName(catalog: Catalog, slug: string): string {
  return catalog?.merchants?.find((m) => m.slug === slug)?.name ?? slug
}

function isSlot(s: unknown): s is Slot {
  return typeof s === 'string' && (SLOTS as readonly string[]).includes(s)
}

/** Keep only SKUs that exist and sit in the right slot; fill required slots from fallback look, persona defaults, then first product. */
function normalizeLook(look: Look | undefined | null, catalog: Catalog, fallback?: Look | null): FullLook {
  const skus = bySku(catalog)
  const valid = (slot: Slot, sku: unknown): string | null =>
    typeof sku === 'string' && skus.get(sku)?.slot === slot ? sku : null
  const out = {} as FullLook
  for (const slot of SLOTS) out[slot] = valid(slot, look?.[slot])
  for (const slot of REQUIRED) {
    if (out[slot]) continue
    out[slot] =
      valid(slot, fallback?.[slot]) ??
      DEFAULT_LOOK.map((s) => valid(slot, s)).find(Boolean) ??
      (catalog?.products ?? []).find((p) => p.slot === slot)?.sku ??
      null
  }
  return out
}

async function postJson(url: string, body: unknown): Promise<unknown> {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } finally {
    clearTimeout(t)
  }
}

// ---------- keyword stylist ----------

const SLOT_WORDS: Record<string, { slot: Slot; kind?: string }> = {
  tee: { slot: 'top', kind: 'tee' }, tees: { slot: 'top', kind: 'tee' }, tshirt: { slot: 'top', kind: 'tee' },
  't-shirt': { slot: 'top', kind: 'tee' }, 'tshirts': { slot: 'top', kind: 'tee' }, 't-shirts': { slot: 'top', kind: 'tee' },
  shirt: { slot: 'top', kind: 'shirt' }, shirts: { slot: 'top', kind: 'shirt' }, top: { slot: 'top' }, kurta: { slot: 'top', kind: 'festive' },
  blazer: { slot: 'outerwear', kind: 'blazer' }, blazers: { slot: 'outerwear', kind: 'blazer' }, jacket: { slot: 'outerwear' },
  coat: { slot: 'outerwear' }, overshirt: { slot: 'outerwear', kind: 'overshirt' }, layer: { slot: 'outerwear' },
  bandhgala: { slot: 'outerwear', kind: 'bandhgala' }, suit: { slot: 'outerwear', kind: 'blazer' },
  trousers: { slot: 'bottom', kind: 'trousers' }, trouser: { slot: 'bottom', kind: 'trousers' }, pants: { slot: 'bottom', kind: 'trousers' },
  jeans: { slot: 'bottom', kind: 'denim' }, denim: { slot: 'bottom', kind: 'denim' }, denims: { slot: 'bottom', kind: 'denim' },
  chinos: { slot: 'bottom', kind: 'chinos' }, chino: { slot: 'bottom', kind: 'chinos' }, bottoms: { slot: 'bottom' }, bottom: { slot: 'bottom' },
  shoes: { slot: 'footwear' }, shoe: { slot: 'footwear' }, sneakers: { slot: 'footwear', kind: 'sneakers' }, sneaker: { slot: 'footwear', kind: 'sneakers' },
  trainers: { slot: 'footwear', kind: 'sneakers' }, runners: { slot: 'footwear', kind: 'runner' }, kicks: { slot: 'footwear', kind: 'sneakers' },
  loafers: { slot: 'footwear', kind: 'loafers' }, loafer: { slot: 'footwear', kind: 'loafers' }, footwear: { slot: 'footwear' },
  cap: { slot: 'headwear', kind: 'cap' }, caps: { slot: 'headwear', kind: 'cap' }, hat: { slot: 'headwear' }, beanie: { slot: 'headwear', kind: 'beanie' },
  bucket: { slot: 'headwear', kind: 'bucket' }, headwear: { slot: 'headwear' },
  glasses: { slot: 'eyewear', kind: 'glasses' }, specs: { slot: 'eyewear', kind: 'glasses' }, spectacles: { slot: 'eyewear', kind: 'glasses' },
  sunglasses: { slot: 'eyewear', kind: 'sunglasses' }, shades: { slot: 'eyewear', kind: 'sunglasses' }, eyewear: { slot: 'eyewear' },
  watch: { slot: 'watch' }, watches: { slot: 'watch' },
  chain: { slot: 'neckwear', kind: 'chain' }, necklace: { slot: 'neckwear', kind: 'chain' }, neckwear: { slot: 'neckwear' },
}

// words that mean the same thing as catalog tags / colour names
const SYNONYMS: Record<string, string[]> = {
  wide: ['wide-leg', 'baggy'], baggy: ['baggy', 'wide-leg', 'oversized'], loose: ['baggy', 'wide-leg', 'oversized', 'relaxed'],
  relaxed: ['relaxed', 'baggy', 'wide-leg'], oversized: ['oversized', 'baggy'], slim: ['slim'], skinny: ['slim'], fitted: ['slim'],
  gray: ['grey'], grey: ['grey', 'charcoal'], navy: ['navy', 'blue'], gold: ['gold', 'yellow'], golden: ['gold'],
  yellow: ['yellow', 'mustard', 'marigold'], orange: ['orange', 'rust', 'marigold'], green: ['green', 'olive'], beige: ['beige', 'stone', 'khaki', 'cream'],
  cream: ['cream', 'off-white'], ivory: ['cream', 'white'], offwhite: ['white', 'cream'], brown: ['brown', 'tan', 'tortoise'],
  maroon: ['maroon', 'red'], burgundy: ['maroon'], red: ['red'], formal: ['formal', 'smart'], smart: ['smart', 'formal', 'smart-casual'],
  bengaluru: ['bangalore', 'bengaluru'], bangalore: ['bangalore', 'bengaluru'], blr: ['bangalore', 'bengaluru'],
  graphic: ['graphic', 'print'], printed: ['print', 'graphic'], striped: ['stripe'], stripes: ['stripe'], checked: ['check'], checks: ['check'],
  street: ['streetwear'], sporty: ['sporty'], ethnic: ['ethnic', 'festive'], traditional: ['ethnic', 'festive'],
  silver: ['silver', 'steel'], metal: ['metal', 'steel'], dark: ['black', 'charcoal'], light: ['white', 'cream', 'stone'],
}

const STOP = new Set(['a', 'an', 'the', 'my', 'me', 'i', 'and', 'with', 'in', 'on', 'for', 'of', 'to', 'some', 'something', 'want',
  'like', 'give', 'make', 'put', 'please', 'look', 'outfit', 'wear', 'wearing', 'pair', 'it', 'this', 'that', 'is', 'be', 'at', 'or', 'from', 'by'])

const FESTIVE = ['KC-010', 'RS-003', 'IL-007', 'KB-004', 'LL-006']

function tokenize(s: string): string[] {
  return (s || '')
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/off-white/g, 'offwhite')
    .replace(/t-shirt/g, 'tshirt')
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
}

function productWords(p: Product, catalog: Catalog): Set<string> {
  const words = new Set<string>()
  const add = (s: string) => tokenize(s).forEach((w) => { words.add(w); w.split('-').forEach((x) => x && words.add(x)) })
  add(p.name); add(p.colorName); p.tags.forEach(add); add(merchantName(catalog, p.merchant))
  return words
}

const COLOURS = new Set(['white', 'black', 'red', 'blue', 'navy', 'grey', 'gray', 'charcoal', 'brown', 'beige', 'stone', 'khaki', 'cream',
  'olive', 'green', 'rust', 'orange', 'maroon', 'yellow', 'mustard', 'marigold', 'gold', 'silver', 'tan', 'tortoise', 'indigo', 'steel', 'offwhite'])

function wordScore(word: string, pw: Set<string>): number {
  if (STOP.has(word)) return 0
  if (pw.has(word)) return COLOURS.has(word) ? 5 : 3
  const syn = SYNONYMS[word]
  if (syn && syn.some((s) => pw.has(s))) return 2
  if (word.endsWith('s') && pw.has(word.slice(0, -1))) return 2
  return 0
}

function bestIn(slot: Slot, words: string[], catalog: Catalog, current: string | null, kind?: string): { sku: string; score: number } | null {
  let best: { sku: string; score: number } | null = null
  for (const p of catalog.products) {
    if (p.slot !== slot) continue
    const pw = productWords(p, catalog)
    let score = 0
    if (kind) score += pw.has(kind) || (kind === 'tee' && pw.has('tee')) ? 4 : 0
    for (const w of words) score += wordScore(w, pw)
    if (p.sku === current) score += 0.5 // prefer keeping what is already worn on a tie
    if (!best || score > best.score) best = { sku: p.sku, score }
  }
  return best
}

function blackFor(slot: Slot, catalog: Catalog): string | null {
  const items = catalog.products.filter((p) => p.slot === slot)
  return (items.find((p) => p.tags.includes('all-black')) ?? items.find((p) => p.tags.includes('black')))?.sku ?? null
}

export function keywordStylist(input: StylistInput, catalog: Catalog): StylistResult {
  const skus = bySku(catalog)
  const current = normalizeLook(input?.currentLook, catalog)
  const look: FullLook = { ...current }
  const prompt = String(input?.prompt ?? '')
  const text = ` ${tokenize(prompt).join(' ')} `
  const tokens = tokenize(prompt)
  const reasons = new Map<Slot, string>()
  const set = (slot: Slot, sku: string | null, why: string) => {
    if (sku && skus.get(sku)?.slot !== slot) return
    look[slot] = sku
    reasons.set(slot, why)
  }
  let title = ''

  // 1. Themes
  const allBlack = /\b(all|head to toe|total|full|monochrome)[ -]?black\b|\bblackout\b|\ball-black\b/.test(text)
  const festive = /\b(festive|diwali|deepavali|wedding|celebration|pooja|puja|ethnic|traditional|sangeet)\b/.test(text)
  const stage = /\b(stage|keynote|talk|presenting|present|presentation|conference|speaker|speech)\b/.test(text)
  if (allBlack) {
    for (const slot of SLOTS) { const b = blackFor(slot, catalog); if (b) set(slot, b, 'all black, head to toe') }
    title = 'All black, stage-ready'
  } else if (festive) {
    for (const sku of FESTIVE) { const p = skus.get(sku); if (p) set(p.slot, sku, 'festive pick for Bangalore') }
    title = 'Festive in Bangalore'
  }
  if (stage && !allBlack && !festive) {
    if (skus.get('RS-001')) set('outerwear', 'RS-001', 'a structured blazer reads sharp under stage lights')
    title = 'Keynote-ready'
  }

  // 2. Explicit slot mentions: "red cap", "white shirt", "baggy trousers"
  let lastBoundary = -1
  const mentioned = new Set<Slot>()
  tokens.forEach((tok, i) => {
    if (tok === 'and' || tok === 'with' || tok === 'plus') { lastBoundary = i; return }
    const hit = SLOT_WORDS[tok]
    if (!hit) return
    const neg = tokens.slice(Math.max(lastBoundary + 1, i - 3), i).some((w) => w === 'no' || w === 'without' || w === 'remove' || w === 'skip' || w === 'lose' || w === 'drop')
    const mods = tokens.slice(Math.max(lastBoundary + 1, i - 3), i).filter((w) => !SLOT_WORDS[w])
    lastBoundary = i
    mentioned.add(hit.slot)
    if (neg) {
      if (!REQUIRED.includes(hit.slot)) set(hit.slot, null, 'removed as asked')
      return
    }
    const best = bestIn(hit.slot, allBlack ? [...mods, 'black'] : mods, catalog, look[hit.slot], hit.kind)
    if (best) set(hit.slot, best.sku, mods.length ? `${mods.join(' ')} ${tok}, as asked` : `${tok}, as asked`)
  })

  // 3. Merchant mentions without a slot word: "something from Kerb"
  for (const m of catalog.merchants ?? []) {
    const name = ` ${tokenize(m.name).join(' ')} `
    if (!text.includes(name)) continue
    const items = catalog.products.filter((p) => p.merchant === m.slug)
    const slots = [...new Set(items.map((p) => p.slot))].filter((s) => !mentioned.has(s))
    for (const slot of slots.slice(0, 1)) {
      const best = bestIn(slot, tokens, { ...catalog, products: items }, look[slot])
      if (best) set(slot, best.sku, `from ${m.name}, as asked`)
    }
  }

  // 4. Style or colour words only ("streetwear", "something blue"): tune worn slots
  if (!reasons.size) {
    const words = tokens.filter((w) => !STOP.has(w))
    const event = tokenize(String(input?.event ?? ''))
    for (const slot of SLOTS) {
      if (!look[slot] && !REQUIRED.includes(slot)) continue
      const best = bestIn(slot, words, catalog, look[slot])
      if (best && best.score >= 2 && best.sku !== look[slot]) set(slot, best.sku, `matches "${words.join(' ')}"`)
    }
    if (!reasons.size && event.some((w) => w === 'diwali' || w === 'festive' || w === 'wedding')) {
      for (const sku of FESTIVE) { const p = skus.get(sku); if (p) set(p.slot, sku, 'festive pick for the occasion') }
      title = 'Festive in Bangalore'
    }
  }

  const final = normalizeLook(look, catalog, current)
  const notes: StylistResult['notes'] = []
  for (const [slot, why] of reasons) {
    const sku = final[slot]
    if (!sku) continue
    const p = skus.get(sku)!
    notes.push({ sku, why: `${p.name} in ${p.colorName} from ${merchantName(catalog, p.merchant)}: ${why}.` })
  }
  return {
    title: title || (notes.length ? 'Your look, tuned' : 'Your look'),
    look: final,
    notes,
    stageNotes: 'Picked by keyword match while the AI stylist is offline. Run the stage check to see how it reads on the LED wall.',
    source: 'keywords',
  }
}

function sanitizeStylist(raw: unknown, input: StylistInput, catalog: Catalog): StylistResult | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  if (!r.look || typeof r.look !== 'object') return null
  const skus = bySku(catalog)
  const look = normalizeLook(r.look as Look, catalog, input?.currentLook)
  if (!REQUIRED.every((s) => look[s])) return null
  const notes = Array.isArray(r.notes)
    ? (r.notes as unknown[])
        .filter((n): n is { sku: string; why: string } =>
          !!n && typeof n === 'object' && typeof (n as { sku?: unknown }).sku === 'string' && typeof (n as { why?: unknown }).why === 'string')
        .filter((n) => skus.has(n.sku))
        .map((n) => ({ sku: n.sku, why: n.why }))
    : []
  return {
    title: typeof r.title === 'string' && r.title.trim() ? r.title.trim() : 'Your look',
    look,
    notes,
    stageNotes: typeof r.stageNotes === 'string' ? r.stageNotes : '',
    source: 'ai',
  }
}

export async function askStylist(input: StylistInput, catalog: Catalog): Promise<StylistResult> {
  try {
    const raw = await postJson('/api/stylist', {
      prompt: String(input?.prompt ?? ''),
      event: String(input?.event ?? ''),
      currentLook: input?.currentLook ?? {},
    })
    const ok = sanitizeStylist(raw, input, catalog)
    if (ok) return ok
  } catch {
    // fall through to keywords
  }
  try {
    return keywordStylist(input, catalog)
  } catch {
    return {
      title: 'Your look',
      look: normalizeLook(input?.currentLook, catalog),
      notes: [],
      stageNotes: '',
      source: 'keywords',
    }
  }
}

// ---------- stage metrics (pure) ----------

function hexToRgb(hex: string): [number, number, number] {
  let h = String(hex || '').trim().replace(/^#/, '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return [0, 0, 0]
  return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255]
}
const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
function luminanceRgb([r, g, b]: [number, number, number]): number {
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}
export function luminance(hex: string): number {
  return luminanceRgb(hexToRgb(hex))
}
export function contrastRatio(a: string, b: string): number {
  const la = luminance(a), lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}
function mix(a: string, b: string, t: number): string {
  const x = hexToRgb(a), y = hexToRgb(b)
  const c = x.map((v, i) => Math.round((v * (1 - t) + y[i] * t) * 255))
  return '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('')
}
/** Apparent garment colour from a distance: patterns blend in a little of their pattern colour. */
function apparentColor(p: Product): string {
  const m = p.material
  if (!m) return '#808080'
  const t = m.pattern === 'stripe' || m.pattern === 'check' ? 0.35 : m.pattern === 'melange' || m.pattern === 'denim' || m.pattern === 'corduroy' ? 0.2 : 0
  return t ? mix(m.color, m.patternColor || m.color, t) : m.color
}

// Warm-white stage spot. Garment luminance under it = per-channel multiply.
const SPOT = '#FFF1DC'
const r2 = (n: number) => Math.round(n * 100) / 100

export function computeStageMetrics(look: Look, catalog: Catalog, ledWallColor: string): StageMetrics {
  const skus = bySku(catalog)
  const items = SLOTS.map((s) => (look?.[s] ? skus.get(look[s] as string) : undefined)).filter(
    (p, i): p is Product => !!p && p.slot === SLOTS[i],
  )
  const get = (slot: Slot) => items.find((p) => p.slot === slot)
  const led = /^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(String(ledWallColor || '')) ? ledWallColor : '#0B1020'
  const outer = get('outerwear')
  const top = get('top')
  const front = outer ?? top
  const spot = hexToRgb(SPOT)
  const lums = items.map((p) => {
    const c = hexToRgb(apparentColor(p))
    return luminanceRgb([c[0] * spot[0], c[1] * spot[1], c[2] * spot[2]])
  })
  const prints = items.filter((p) => p.material?.printText)
  return {
    ledWallColor: led.startsWith('#') ? led : `#${led}`,
    topContrast: front ? r2(contrastRatio(apparentColor(front), led)) : 1,
    outerwearContrast: outer ? r2(contrastRatio(apparentColor(outer), led)) : null,
    brightnessUnderSpots: lums.length ? r2(lums.reduce((a, b) => a + b, 0) / lums.length) : 0,
    printReadability: prints.length
      ? r2(Math.min(...prints.map((p) => contrastRatio(p.material.patternColor, p.material.color))))
      : null,
    merchants: new Set(items.map((p) => p.merchant)).size,
    total: items.reduce((a, p) => a + (p.price || 0), 0),
  }
}

// ---------- rules stage check ----------

function bestContrastSwap(look: Look, catalog: Catalog, led: string): StageCheckResult['swap'] {
  const skus = bySku(catalog)
  const tryslot = (slot: Slot): StageCheckResult['swap'] => {
    const cur = look?.[slot] ? skus.get(look[slot] as string) : undefined
    if (!cur) return null
    const curC = contrastRatio(apparentColor(cur), led)
    let best: Product | null = null, bestC = curC
    for (const p of catalog.products) {
      if (p.slot !== slot || p.sku === cur.sku) continue
      const c = contrastRatio(apparentColor(p), led)
      if (c > bestC) { best = p; bestC = c }
    }
    if (!best || bestC - curC < 0.75 || curC >= 7) return null
    const lighter = luminance(apparentColor(best)) > luminance(apparentColor(cur))
    return {
      slot,
      sku: best.sku,
      why: `${best.name} in ${best.colorName} from ${merchantName(catalog, best.merchant)} lifts contrast against the LED wall from ${r2(curC)}:1 to ${r2(bestC)}:1${lighter ? ', a lighter layer that will not melt into the screen' : ''}.`,
    }
  }
  return look?.outerwear ? tryslot('outerwear') ?? tryslot('top') : tryslot('top')
}

export function rulesStageCheck(look: Look, metrics: StageMetrics, catalog: Catalog): StageCheckResult {
  const m = metrics ?? computeStageMetrics(look, catalog, '#0B1020')
  const skus = bySku(catalog)
  const front = look?.outerwear ? skus.get(look.outerwear) : look?.top ? skus.get(look.top) : undefined
  const frontName = front ? front.name.toLowerCase() : 'top'
  const c = m.topContrast || 1
  const b = m.brightnessUnderSpots || 0
  const contrastPts = Math.max(0, Math.min(1, (c - 1) / (4.5 - 1))) * 55
  const brightPts = b < 0.04 ? 10 : b < 0.1 ? 20 : b <= 0.6 ? 30 : b <= 0.75 ? 22 : 14
  const printPts = m.printReadability == null ? 10 : Math.max(0, Math.min(1, (m.printReadability - 1) / (3 - 1))) * 10
  const requiredPts = REQUIRED.every((s) => look?.[s]) ? 5 : 0
  const score = Math.round(Math.max(0, Math.min(100, contrastPts + brightPts + printPts + requiredPts)))
  const verdict =
    score >= 80 ? 'Stage-ready: you will pop against the wall.' : score >= 60 ? 'Good, one tweak away from great.' : 'Risky on stage: you may blend into the LED wall.'
  const notes = [
    c >= 4.5
      ? `Your ${frontName} reads at ${r2(c)}:1 against the LED wall, strong separation from the screen.`
      : c >= 3
        ? `Your ${frontName} reads at ${r2(c)}:1 against the LED wall; fine, but 4.5:1 would really pop on camera.`
        : `Your ${frontName} reads at only ${r2(c)}:1 against the LED wall; you risk melting into the screen.`,
    b < 0.1
      ? 'The look is very dark under the spots; detail and texture will disappear on the livestream.'
      : b > 0.65
        ? 'Lots of bright surfaces under the spots; watch for glare and blown-out whites on camera.'
        : 'Brightness under the spots is balanced, so fabric texture will hold up on camera.',
    m.printReadability != null
      ? m.printReadability >= 3
        ? `The print is legible at ${r2(m.printReadability)}:1, the back rows will read it.`
        : `The print only reaches ${r2(m.printReadability)}:1; it will be hard to read past the front row.`
      : `${m.merchants} independent ${m.merchants === 1 ? 'store' : 'stores'}, Rs ${Math.round(m.total).toLocaleString('en-IN')} for the full look.`,
  ]
  const swap = c < 4.5 ? bestContrastSwap(look, catalog, m.ledWallColor) : null
  return { score, verdict, notes, swap, source: 'rules' }
}

function sanitizeStageCheck(raw: unknown, catalog: Catalog, fallback: StageCheckResult): StageCheckResult | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  const score = Number(r.score)
  if (!Number.isFinite(score)) return null
  if (typeof r.verdict !== 'string' || !r.verdict.trim()) return null
  const notes = Array.isArray(r.notes) ? (r.notes as unknown[]).filter((n): n is string => typeof n === 'string' && !!n.trim()) : []
  if (!notes.length) return null
  while (notes.length < 3) notes.push(fallback.notes[notes.length] ?? '')
  let swap: StageCheckResult['swap'] = null
  const s = r.swap as Record<string, unknown> | null | undefined
  if (s && typeof s === 'object' && isSlot(s.slot) && typeof s.sku === 'string') {
    const p = bySku(catalog).get(s.sku)
    if (p && p.slot === s.slot) swap = { slot: s.slot, sku: s.sku, why: typeof s.why === 'string' ? s.why : '' }
  }
  return {
    score: Math.round(Math.max(0, Math.min(100, score))),
    verdict: r.verdict.trim(),
    notes: notes.slice(0, 3),
    swap,
    source: 'ai',
  }
}

export async function stageCheck(look: Look, metrics: StageMetrics, catalog: Catalog): Promise<StageCheckResult> {
  let rules: StageCheckResult
  try {
    rules = rulesStageCheck(look, metrics, catalog)
  } catch {
    rules = { score: 70, verdict: 'Looks good on stage.', notes: ['Check your contrast against the LED wall.', 'Keep textures visible under the spots.', 'Make sure the full look is in the bag.'], swap: null, source: 'rules' }
  }
  try {
    const raw = await postJson('/api/stagecheck', { look, metrics })
    const ok = sanitizeStageCheck(raw, catalog, rules)
    if (ok) return ok
  } catch {
    // fall through to rules
  }
  return rules
}
