// Vercel Node function: POST /api/stagecheck (Lane D2). Scores how a look reads on stage, structured output.
import Anthropic from '@anthropic-ai/sdk'
import type { IncomingMessage, ServerResponse } from 'node:http'

// ---- shared (kept inline so each Vercel function is a single self-contained file) ----

type Req = IncomingMessage & { body?: unknown }
const SLOTS = ['top', 'outerwear', 'bottom', 'footwear', 'headwear', 'eyewear', 'watch', 'neckwear'] as const
type Slot = (typeof SLOTS)[number]
const REQUIRED: Slot[] = ['top', 'bottom', 'footwear']
// Persona default look and the demo Stage Ready look. These mirror web/src/config.ts (DEFAULT_LOOK, STAGE_READY);
// the live catalog's defaultLook and looks win when present.
let defaultLookSkus: string[] = ['KT-002', 'KT-006', 'SW-001', 'KK-001', 'LL-006', 'SH-001']
let stageReady: { title: string; skus: string[] } = { title: 'Stage Ready', skus: ['KT-001', 'KT-006', 'SW-001', 'KK-001', 'LL-001', 'LL-006', 'SH-001'] }
function slotMap(skus: string[], products: P[]): Partial<Record<Slot, string>> {
  const m = new Map(products.map((p) => [p.sku, p]))
  const out: Partial<Record<Slot, string>> = {}
  for (const sku of skus) {
    const p = m.get(sku)
    if (p && !out[p.slot]) out[p.slot] = sku
  }
  return out
}
const STAGE_WASH = { cobalt: '#2D4BFF', ultraviolet: '#7A5CFF' }
const PRIMARY_MODEL = process.env.STYLIST_MODEL || 'claude-haiku-5-5'
const RETRY_MODEL = 'claude-sonnet-5-5'
const BUDGET_MS = 8300 // client gives up at 9 s

type P = {
  sku: string; name: string; colorName: string; slot: Slot; merchant: string; price: number; tags: string[]
  color: string; pattern: string; patternColor: string; printText: string
  oneOfOne: boolean; condition: string; size: string; era: string
}

// Fallback copy of web/public/catalog/catalog.json (sku|name|colour|slot|store|price|tags|hex|pattern|patternHex|print|oneOfOne|condition|size|era).
// The live catalog is fetched from the deployment first, so catalog edits flow through without touching this file.
const SNAPSHOT = `KT-001|Crisp White Oxford Shirt|White|top|Kaapi Thrift|899|white,shirt,oxford,formal,smart,classic,stage|#F4F3EE|solid|#F4F3EE||1|9/10|M|2010s
KT-002|Black Poplin Shirt|Black|top|Kaapi Thrift|799|black,shirt,poplin,all-black,evening,smart|#121212|solid|#121212||1|9/10|M|2010s
KT-003|Ecru Heavyweight Tee|Ecru|top|Kaapi Thrift|549|ecru,cream,white,tee,heavyweight,basic,casual|#EDE4D3|melange|#DCCFB7||1|8/10|L|2000s
KT-004|Washed Black Boxy Tee|Washed Black|top|Kaapi Thrift|599|black,tee,boxy,oversized,baggy,streetwear,all-black|#1D1D1F|melange|#2A2A2E||1|8/10|L|2000s
KT-005|BLR Graphic Boxy Tee|Off-White|top|Kaapi Thrift|699|white,tee,graphic,print,bangalore,bengaluru,boxy,oversized|#EFE8DA|print|#1A1A1A|BLR|1|9/10|XL|2010s
KT-006|Beige Linen Overshirt|Beige|outerwear|Kaapi Thrift|1299|beige,linen,overshirt,layer,stage,smart-casual,summer|#CDBA9A|melange|#BFAA86||1|9/10|L|2010s
KT-007|Charcoal Thrifted Blazer|Charcoal|outerwear|Kaapi Thrift|1799|charcoal,grey,blazer,formal,keynote,smart|#3A3B3F|solid|#3A3B3F||1|8/10|40|1990s
KT-008|Madras Check Shirt|Red Madras|top|Kaapi Thrift|849|red,navy,check,madras,shirt,festive,bold|#B22234|check|#22306B||1|9/10|M|1990s
SW-001|Light-Wash Baggy Jeans|Light Wash|bottom|Stonewash Society|1199|blue,light-wash,denim,jeans,baggy,wide-leg,relaxed,streetwear|#9FB7CC|denim|#7F98B0||1|9/10|32|2000s
SW-002|Raw Indigo Wide-Leg Jeans|Raw Indigo|bottom|Stonewash Society|1299|blue,indigo,denim,jeans,wide-leg,dark|#253A66|denim|#1B2B4D||1|9/10|32|2010s
SW-003|Black Baggy Cargos|Black|bottom|Stonewash Society|1099|black,cargos,baggy,utility,all-black,streetwear|#151515|solid|#151515||1|8/10|32|2000s
SW-004|Stone Pleated Trousers|Stone|bottom|Stonewash Society|999|beige,stone,pleated,trousers,wide-leg,smart,festive|#CBBFA8|solid|#CBBFA8||1|9/10|32|1990s
SW-005|Slim Charcoal Trousers|Charcoal|bottom|Stonewash Society|899|charcoal,grey,slim,trousers,formal,smart|#3B3D42|solid|#3B3D42||1|8/10|32|2010s
SW-006|Washed Grey Slim Jeans|Washed Grey|bottom|Stonewash Society|849|grey,denim,jeans,slim,casual|#8A8F98|denim|#6F747D||1|8/10|32|2010s
KK-001|Clean White Court Sneakers|White|footwear|Kerbside Kicks|2499|white,sneakers,court,minimal,classic,stage|#F4F4F2|solid|#F4F4F2||1|9/10|UK 9|2020s
KK-002|Black and Gum Sneakers|Black / Gum|footwear|Kerbside Kicks|2299|black,gum,sneakers,casual,streetwear|#1A1A1A|solid|#1A1A1A||1|8/10|UK 9|2010s
KK-003|Red Retro Runners|Red|footwear|Kerbside Kicks|2799|red,sneakers,runners,retro,bold,sporty|#C8302B|solid|#C8302B||1|8/10|UK 9|1990s
KK-004|Tan Penny Loafers|Tan|footwear|Kerbside Kicks|1999|tan,brown,loafers,smart,festive,formal|#8B5A2B|solid|#8B5A2B||1|9/10|UK 9|2000s
KK-005|Black Leather Loafers|Black|footwear|Kerbside Kicks|2199|black,loafers,leather,formal,all-black,evening|#121212|solid|#121212||1|9/10|UK 9|2010s
LL-001|Red Six-Panel Cap|Red|headwear|Lids & Lenses|499|red,cap,six-panel,baseball,bold,streetwear|#C62828|solid|#C62828||1|9/10|Free|2000s
LL-002|Washed Black Cap|Washed Black|headwear|Lids & Lenses|449|black,cap,baseball,all-black|#1F1F1F|solid|#1F1F1F||1|8/10|Free|2010s
LL-003|Cream Corduroy Cap|Cream|headwear|Lids & Lenses|549|cream,white,cap,corduroy,vintage|#E9DFC9|corduroy|#D9CDB2||1|9/10|Free|1990s
LL-004|Rust Rib Beanie|Rust|headwear|Lids & Lenses|399|rust,orange,beanie,knit,winter,casual|#A6461F|melange|#8E3A18||1|9/10|Free|2010s
LL-005|Khaki Bucket Hat|Khaki|headwear|Lids & Lenses|549|khaki,beige,bucket,hat,streetwear,vintage|#B8A77A|solid|#B8A77A||1|8/10|Free|1990s
LL-006|Thin Gold Hex Frames|Gold|eyewear|Lids & Lenses|799|gold,glasses,frames,hexagonal,metal,optical,classic|#C9A55A|solid|#C9A55A||1|9/10|One size|2010s
LL-007|Black Square Shades|Black|eyewear|Lids & Lenses|699|black,sunglasses,shades,square,bold,all-black|#0E0E0E|solid|#0E0E0E||1|8/10|One size|1990s
SH-001|Gold Digital Watch|Gold|watch|Second Hand|1899|gold,watch,digital,retro,metal,festive,stage|#D4AF37|solid|#D4AF37||1|9/10|One size|1990s
SH-002|Steel Field Watch|Steel|watch|Second Hand|2499|silver,steel,watch,analog,field,classic|#B8BCC2|solid|#B8BCC2||1|8/10|One size|1980s
SH-003|Black Digital Sports Watch|Black|watch|Second Hand|1499|black,watch,digital,sports,all-black,casual|#151515|solid|#151515||1|8/10|One size|2000s
SH-004|Silver Rope Chain|Silver|neckwear|Second Hand|599|silver,chain,rope,metal,streetwear|#C0C0C0|solid|#C0C0C0||1|9/10|20 in|2000s
SH-005|Gold Curb Chain|Gold|neckwear|Second Hand|699|gold,chain,curb,metal,festive|#D4AF37|solid|#D4AF37||1|9/10|20 in|1990s`

function parseSnapshot(): P[] {
  return SNAPSHOT.trim().split('\n').map((l) => {
    const [sku, name, colorName, slot, merchant, price, tags, color, pattern, patternColor, printText, oneOfOne, condition, size, era] = l.split('|')
    return {
      sku, name, colorName, slot: slot as Slot, merchant, price: Number(price), tags: tags ? tags.split(',') : [], color, pattern, patternColor,
      printText: printText || '', oneOfOne: oneOfOne !== '0', condition: condition || '', size: size || '', era: era || '',
    }
  })
}

let cache: { at: number; products: P[] } | null = null
let catalogSource: 'live' | 'snapshot' = 'snapshot'

async function loadCatalog(req: Req): Promise<P[]> {
  if (cache && Date.now() - cache.at < 5 * 60_000) return cache.products
  try {
    const hdr = String(req.headers['x-forwarded-host'] || req.headers.host || '')
    const host = process.env.VERCEL_PROJECT_PRODUCTION_URL || (/(\.vercel\.app|^localhost(:\d+)?)$/.test(hdr) ? hdr : '')
    if (host) {
      const proto = host.startsWith('localhost') ? 'http' : 'https'
      const r = await fetch(`${proto}://${host}/catalog/catalog.json`, { signal: AbortSignal.timeout(1500) })
      if (r.ok) {
        const j = (await r.json()) as {
          defaultLook?: string[]
          looks?: { title: string; skus: string[] }[]
          merchants: { slug: string; name: string }[]
          products: {
            sku: string; name: string; colorName: string; slot: Slot; merchant: string; price: number; tags: string[]
            oneOfOne?: boolean; condition?: string; size?: string; era?: string
            material: { color: string; pattern: string; patternColor: string; printText: string | null }
          }[]
        }
        const mn = new Map(j.merchants.map((m) => [m.slug, m.name]))
        const products: P[] = j.products
          .filter((p) => (SLOTS as readonly string[]).includes(p.slot))
          .map((p) => ({
            sku: p.sku, name: p.name, colorName: p.colorName, slot: p.slot, merchant: mn.get(p.merchant) ?? p.merchant,
            price: p.price, tags: p.tags ?? [], color: p.material?.color ?? '#808080', pattern: p.material?.pattern ?? 'solid',
            patternColor: p.material?.patternColor ?? p.material?.color ?? '#808080', printText: p.material?.printText ?? '',
            oneOfOne: p.oneOfOne !== false, condition: p.condition ?? '', size: p.size ?? '', era: p.era ?? '',
          }))
        if (products.length) {
          if (Array.isArray(j.defaultLook) && j.defaultLook.length) defaultLookSkus = j.defaultLook.filter((x) => typeof x === 'string')
          const ready = j.looks?.find((l) => l?.title === stageReady.title) ?? j.looks?.[0]
          if (ready && typeof ready.title === 'string' && Array.isArray(ready.skus) && ready.skus.length) stageReady = { title: ready.title, skus: ready.skus }
          cache = { at: Date.now(), products }
          catalogSource = 'live'
          return products
        }
      }
    }
  } catch {
    // use the snapshot
  }
  const products = parseSnapshot()
  catalogSource = 'snapshot'
  cache = { at: Date.now() - 4 * 60_000, products } // retry the live catalog in a minute
  return products
}

async function readBody(req: Req): Promise<unknown> {
  if (req.body !== undefined && req.body !== null && req.body !== '') {
    if (typeof req.body === 'string') return JSON.parse(req.body)
    if (Buffer.isBuffer(req.body)) return JSON.parse(req.body.toString('utf8'))
    return req.body
  }
  const chunks: Buffer[] = []
  for await (const c of req) chunks.push(typeof c === 'string' ? Buffer.from(c) : (c as Buffer))
  const s = Buffer.concat(chunks).toString('utf8')
  return s ? JSON.parse(s) : {}
}

function send(res: ServerResponse, status: number, data: unknown) {
  res.statusCode = status
  res.setHeader('content-type', 'application/json; charset=utf-8')
  res.setHeader('cache-control', 'no-store')
  res.setHeader('access-control-allow-origin', '*')
  res.setHeader('access-control-allow-methods', 'POST, OPTIONS')
  res.setHeader('access-control-allow-headers', 'content-type')
  res.end(JSON.stringify(data))
}

function preflight(req: Req, res: ServerResponse): boolean {
  if (req.method === 'OPTIONS') { send(res, 204, {}); return true }
  if (req.method !== 'POST') { send(res, 405, { error: 'POST only' }); return true }
  return false
}

// Small in-memory answer cache (per warm instance) so a repeated demo request is instant.
const memo = new Map<string, { at: number; body: Record<string, unknown> }>()
function memoGet(key: string): Record<string, unknown> | null {
  const e = memo.get(key)
  if (e && Date.now() - e.at < 15 * 60_000) return e.body
  if (e) memo.delete(key)
  return null
}
function memoSet(key: string, body: Record<string, unknown>) {
  if (memo.size >= 200) memo.delete(memo.keys().next().value as string)
  memo.set(key, { at: Date.now(), body })
}

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)

let client: Anthropic | null = null
function anthropic(): Anthropic {
  if (!client) client = new Anthropic({ maxRetries: 0 })
  return client
}

/** One structured-output call. Haiku runs with thinking off for latency; Sonnet 5.5 rejects disabled, so it runs adaptive at low effort. */
async function callModel(model: string, system: string, user: string, schema: Record<string, unknown>, maxTokens: number, timeoutMs: number): Promise<unknown> {
  const params: Anthropic.MessageCreateParamsNonStreaming = {
    model,
    max_tokens: maxTokens,
    system: [{ type: 'text', text: system, cache_control: { type: 'ephemeral' } }],
    messages: [{ role: 'user', content: user }],
    output_config: { effort: 'low', format: { type: 'json_schema', schema } },
  }
  if (model.includes('haiku')) params.thinking = { type: 'disabled' }
  const msg = await anthropic().messages.create(params, { timeout: timeoutMs, maxRetries: 0 })
  if (msg.stop_reason === 'refusal') throw new Error('refusal')
  if (msg.stop_reason === 'max_tokens') throw new Error('max_tokens')
  const text = msg.content.map((b) => (b.type === 'text' ? b.text : '')).join('')
  return JSON.parse(text)
}

/** Primary model, then one retry on the fallback model if time allows. */
async function callWithRetry(system: string, user: string, schema: Record<string, unknown>, maxTokens: number): Promise<{ data: unknown; model: string }> {
  const t0 = Date.now()
  try {
    return { data: await callModel(PRIMARY_MODEL, system, user, schema, maxTokens, 5500), model: PRIMARY_MODEL }
  } catch (e) {
    const left = BUDGET_MS - (Date.now() - t0)
    const err = e instanceof Anthropic.APIError ? `${e.status ?? ''} ${e.name}` : e instanceof Error ? e.message : 'error'
    console.warn(`model ${PRIMARY_MODEL} failed (${err}); ${left} ms left`)
    if (left < 2500 || PRIMARY_MODEL === RETRY_MODEL) throw e
    return { data: await callModel(RETRY_MODEL, system, user, schema, maxTokens, left), model: RETRY_MODEL }
  }
}

function errText(e: unknown): string {
  if (e instanceof Anthropic.APIError) return `model error ${e.status ?? ''}`.trim()
  if (e instanceof Error) return e.message.slice(0, 120)
  return 'model error'
}

// ---- /api/stagecheck ----
// In: { look, metrics }  Out: { score 0..100, verdict, notes (exactly three), swap {slot, sku, why} | null, source: 'ai' }

function rgb(hex: string): [number, number, number] {
  let h = String(hex || '').replace(/^#/, '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return [0, 0, 0]
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255) as [number, number, number]
}
function lum(hex: string): number {
  const f = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
  const [r, g, b] = rgb(hex)
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
function contrast(a: string, b: string): number {
  const x = lum(a), y = lum(b)
  return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100
}

const SYSTEM = `You are the stage check for Hrishikesh's look: he presents on stage at the Bluehost AI Builder Tour in Bengaluru, in front of an LED wall, under a stage wash that runs from cobalt (${STAGE_WASH.cobalt}) to ultraviolet (${STAGE_WASH.ultraviolet}) with warm key spots, on a livestream. His look is one-of-one thrift pieces from Kaapi Thrift, Stonewash Society, Kerbside Kicks, Lids & Lenses and Second Hand. You get numbers computed in code and the outfit. Judge how the look will read on stage and on camera.

Guide:
- topContrast is the WCAG contrast of his front garment (outerwear if worn, else top) against the LED wall colour (ledWallColor, part of the cobalt-to-ultraviolet wash): 4.5 or more pops, 3 to 4.5 is fine, under 3 he melts into the screen.
- topUnderContrast (only when outerwear is worn) is the top showing in the V of the jacket against the wall; a light top there also separates him from the screen, so weigh it at about a third.
- brightnessUnderSpots is mean relative luminance of the garments under the spots: 0.1 to 0.6 is balanced, under 0.08 detail disappears on camera, over 0.7 risks glare.
- printReadability is the contrast of any print against its garment (3 or more reads from the back rows); null means no print.
- baselineScore is computed in code from these numbers with the same rules; your score must stay within 6 points of it (85+ stage-ready, 60 to 84 good with a tweak, under 60 risky).
- verdict: one short sentence. note1..note3: three different one-line observations (under 22 words each), concrete and warm, like a stylist backstage.
- swap: pick one of the computed swap candidates (each raises contrast across the whole cobalt-to-ultraviolet wash; a lighter top or layer against the dark blue), or null if there are none or baselineScore is 85 or more. why: one sentence under 25 words that names the store and that the piece is 1 of 1.
Speak to Hrishikesh directly as "you". No emojis.`

function stageSchema(products: P[]): Record<string, unknown> {
  return {
    type: 'object',
    properties: {
      score: { type: 'integer' },
      verdict: { type: 'string' },
      note1: { type: 'string' },
      note2: { type: 'string' },
      note3: { type: 'string' },
      swap: {
        anyOf: [
          {
            type: 'object',
            properties: { slot: { type: 'string', enum: [...SLOTS] }, sku: { type: 'string', enum: products.map((p) => p.sku) }, why: { type: 'string' } },
            required: ['slot', 'sku', 'why'],
            additionalProperties: false,
          },
          { type: 'null' },
        ],
      },
    },
    required: ['score', 'verdict', 'note1', 'note2', 'note3', 'swap'],
    additionalProperties: false,
  }
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

export default async function handler(req: Req, res: ServerResponse) {
  if (preflight(req, res)) return
  const t0 = Date.now()
  let body: unknown
  try {
    body = await readBody(req)
  } catch {
    return send(res, 400, { error: 'invalid JSON' })
  }
  if (!isObj(body) || !isObj(body.look) || !isObj(body.metrics)) return send(res, 400, { error: 'look and metrics objects are required' })
  const m = body.metrics
  const led = typeof m.ledWallColor === 'string' && /^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(m.ledWallColor) ? (m.ledWallColor.startsWith('#') ? m.ledWallColor : `#${m.ledWallColor}`) : STAGE_WASH.cobalt
  if (num(m.topContrast) === null || num(m.brightnessUnderSpots) === null) return send(res, 400, { error: 'metrics need topContrast and brightnessUnderSpots' })

  const products = await loadCatalog(req)
  const bySku = new Map(products.map((p) => [p.sku, p]))
  const look: Partial<Record<Slot, string>> = {}
  for (const slot of SLOTS) {
    const v = body.look[slot]
    if (typeof v === 'string' && bySku.get(v)?.slot === slot) look[slot] = v
  }
  if (!Object.keys(look).length) return send(res, 400, { error: 'look has no known SKUs' })

  const metrics = {
    ledWallColor: led,
    topContrast: num(m.topContrast),
    outerwearContrast: num(m.outerwearContrast),
    brightnessUnderSpots: num(m.brightnessUnderSpots),
    printReadability: num(m.printReadability),
    merchants: num(m.merchants),
    total: num(m.total),
    topUnderContrast: look.outerwear && look.top ? contrast(bySku.get(look.top)!.color, led) : null,
    baselineScore: 0,
  }
  // Same scoring as the client rules fallback (web/src/api/stylist.ts rulesStageCheck), so AI and rules agree.
  {
    const c = metrics.topContrast ?? 1
    const b = metrics.brightnessUnderSpots ?? 0
    const eff = metrics.topUnderContrast != null ? 0.65 * c + 0.35 * Math.min(metrics.topUnderContrast, 7) : c
    const contrastPts = Math.max(0, Math.min(1, (eff - 1) / 3.5)) * 55
    const brightPts = b < 0.04 ? 10 : b < 0.1 ? 20 : b <= 0.6 ? 30 : b <= 0.75 ? 22 : 14
    const printPts = metrics.printReadability == null ? 10 : Math.max(0, Math.min(1, (metrics.printReadability - 1) / 2)) * 10
    const requiredPts = REQUIRED.every((s) => look[s]) ? 5 : 0
    metrics.baselineScore = Math.round(Math.max(0, Math.min(100, contrastPts + brightPts + printPts + requiredPts)))
  }
  const outfit = SLOTS.map((s) => {
    const p = look[s] ? bySku.get(look[s] as string) : undefined
    return `${s}: ${p ? `${p.sku} ${p.name}, ${p.colorName} ${p.color}${p.pattern !== 'solid' ? ` (${p.pattern})` : ''}${p.printText ? ` print "${p.printText}"` : ''}, ${p.merchant}` : 'empty'}`
  }).join('\n')
  // Worst-case contrast across the wash: the LED wall colour and the ultraviolet end.
  const washContrast = (hex: string) => Math.min(contrast(hex, led), contrast(hex, STAGE_WASH.ultraviolet))
  // Swap candidates computed in code: same slot as the front garment (or the top under a jacket), clearly higher contrast.
  const candidates: { p: P; from: number; to: number }[] = []
  for (const slot of (look.outerwear ? ['outerwear', 'top'] : ['top']) as Slot[]) {
    const cur = look[slot] ? bySku.get(look[slot] as string) : undefined
    if (!cur) continue
    const from = washContrast(cur.color)
    if (from >= 7) continue
    products
      .filter((p) => p.slot === slot && p.sku !== cur.sku)
      .map((p) => ({ p, from, to: washContrast(p.color) }))
      .filter((c) => c.to - c.from >= 0.75)
      .sort((a, b) => b.to - a.to)
      .slice(0, 3)
      .forEach((c) => candidates.push(c))
  }
  const options = candidates.length
    ? candidates.map((c) => `${c.p.sku}|${c.p.slot}|${c.p.name}|${c.p.colorName}|${c.p.merchant}|contrast ${c.from} -> ${c.to}`).join('\n')
    : 'none (swap must be null)'
  const user = `Metrics: ${JSON.stringify(metrics)}\n\nOutfit:\n${outfit}\n\nSwap candidates (sku|slot|name|colour|store|worst-case contrast across the wash now -> after):\n${options}`

  const key = JSON.stringify([look, metrics])
  const hit = memoGet(key)
  if (hit) return send(res, 200, { ...hit, cached: true, ms: Date.now() - t0 })

  let out: { data: unknown; model: string }
  try {
    out = await callWithRetry(SYSTEM, user, stageSchema(products), 600)
  } catch (e) {
    console.error('stagecheck failed:', errText(e))
    return send(res, 502, { error: errText(e) })
  }
  const d = isObj(out.data) ? out.data : {}
  const score = num(d.score)
  const notes = [d.note1, d.note2, d.note3].map((n) => (typeof n === 'string' ? n.trim().slice(0, 240) : ''))
  if (score === null || typeof d.verdict !== 'string' || notes.some((n) => !n)) return send(res, 502, { error: 'invalid model output' })
  let swap: { slot: Slot; sku: string; why: string } | null = null
  const pick = isObj(d.swap) && typeof d.swap.sku === 'string' ? candidates.find((c) => c.p.sku === (d.swap as Record<string, unknown>).sku) : undefined
  if (pick && metrics.baselineScore < 85) {
    const why = isObj(d.swap) && typeof d.swap.why === 'string' ? d.swap.why.trim().slice(0, 240) : ''
    swap = { slot: pick.p.slot, sku: pick.p.sku, why: why || `${pick.p.name} from ${pick.p.merchant} lifts contrast against the LED wall from ${pick.from}:1 to ${pick.to}:1.` }
  } else if (isObj(d.swap) && candidates.length && metrics.baselineScore < 85) {
    const c = candidates[0]
    swap = { slot: c.p.slot, sku: c.p.sku, why: `${c.p.name} in ${c.p.colorName} from ${c.p.merchant} lifts contrast against the LED wall from ${c.from}:1 to ${c.to}:1.` }
  }
  const result = {
    score: Math.round(Math.max(0, Math.min(100, Math.max(metrics.baselineScore - 6, Math.min(metrics.baselineScore + 6, score))))),
    verdict: d.verdict.trim().slice(0, 160),
    notes,
    swap,
    source: 'ai',
    model: out.model,
    catalog: catalogSource,
  }
  memoSet(key, result)
  return send(res, 200, { ...result, ms: Date.now() - t0 })
}
