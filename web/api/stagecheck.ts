// Vercel Node function: POST /api/stagecheck (Lane D2). Scores how a look reads on stage, structured output.
import Anthropic from '@anthropic-ai/sdk'
import type { IncomingMessage, ServerResponse } from 'node:http'

// ---- shared (kept inline so each Vercel function is a single self-contained file) ----

type Req = IncomingMessage & { body?: unknown }
const SLOTS = ['top', 'outerwear', 'bottom', 'footwear', 'headwear', 'eyewear', 'watch', 'neckwear'] as const
type Slot = (typeof SLOTS)[number]
const REQUIRED: Slot[] = ['top', 'bottom', 'footwear']
const DEFAULTS: Partial<Record<Slot, string>> = { top: 'KC-001', outerwear: 'RS-001', bottom: 'IL-005', footwear: 'KB-001' }
const PRIMARY_MODEL = process.env.STYLIST_MODEL || 'claude-haiku-5-5'
const RETRY_MODEL = 'claude-sonnet-5-5'
const BUDGET_MS = 8300 // client gives up at 9 s

type P = {
  sku: string; name: string; colorName: string; slot: Slot; merchant: string; price: number; tags: string[]
  color: string; pattern: string; patternColor: string; printText: string
}

// Fallback copy of web/public/catalog/catalog.json (sku|name|colour|slot|merchant|price|tags|hex|pattern|patternHex|print).
// The live catalog is fetched from the deployment first, so catalog edits flow through without touching this file.
const SNAPSHOT = `KC-001|Everyday Tee|White|top|Kaapi Club|799|white,basic,classic,minimal,stage|#F4F2EE|solid|#F4F2EE|
KC-002|Everyday Tee|Black|top|Kaapi Club|799|black,basic,all-black,minimal|#1B1B1D|solid|#1B1B1D|
KC-003|Decoction Oversized Tee|Coffee Brown|top|Kaapi Club|1199|brown,oversized,baggy,streetwear,casual|#5B3A29|solid|#5B3A29|
KC-004|Ship It Oversized Tee|Off-White|top|Kaapi Club|1299|white,print,graphic,oversized,tech,startup|#EFEAE0|print|#C0392B|SHIP IT
KC-005|BLR Graphic Tee|Black|top|Kaapi Club|999|black,print,graphic,bangalore,bengaluru,city|#161616|print|#F2C14E|BLR
KC-006|Oxford Shirt|White|top|Kaapi Club|1899|white,shirt,formal,smart,classic,stage|#FAFAF7|solid|#FAFAF7|
KC-007|Linen Shirt|Sky Blue|top|Kaapi Club|2199|blue,shirt,linen,summer,smart-casual|#A9C7E3|solid|#A9C7E3|
KC-008|Breton Stripe Tee|Navy Stripe|top|Kaapi Club|1099|stripe,navy,white,casual,classic|#F3F1EA|stripe|#1F2A44|
KC-009|Melange Tee|Grey Melange|top|Kaapi Club|899|grey,melange,basic,casual|#9A9A9C|melange|#C9C9CB|
KC-010|Festive Mandarin Shirt|Marigold|top|Kaapi Club|2499|yellow,marigold,festive,ethnic,diwali,celebration,bangalore|#D98E04|solid|#D98E04|
RS-001|Stage Blazer|Charcoal|outerwear|Rao & Sons|6999|charcoal,grey,blazer,formal,stage,keynote,smart|#3A3B3F|solid|#3A3B3F|
RS-002|Midnight Blazer|Black|outerwear|Rao & Sons|7499|black,blazer,all-black,formal,evening|#141416|solid|#141416|
RS-003|Bandhgala-Cut Blazer|Royal Maroon|outerwear|Rao & Sons|8999|maroon,red,festive,ethnic,wedding,blazer,bangalore|#6E1423|solid|#6E1423|
RS-004|Check Overshirt|Olive Check|outerwear|Rao & Sons|3499|olive,green,check,overshirt,casual,layer|#5B6B3A|check|#2E3520|
RS-005|Corduroy Overshirt|Rust|outerwear|Rao & Sons|3999|rust,orange,brown,corduroy,overshirt,casual|#A0522D|corduroy|#7E3F22|
IL-001|Baggy Wide-Leg Trousers|Stone|bottom|Indigo Loom|2799|beige,stone,baggy,wide-leg,relaxed,streetwear|#C8BBA3|solid|#C8BBA3|
IL-002|Wide-Leg Denim|Mid Indigo|bottom|Indigo Loom|3299|blue,denim,jeans,wide-leg,baggy,casual|#2C3E66|denim|#4A5F8C|
IL-003|Slim Selvedge Denim|Raw Indigo|bottom|Indigo Loom|3499|blue,denim,jeans,slim,classic|#1E2A47|denim|#33456E|
IL-004|Slim Chinos|Black|bottom|Indigo Loom|2299|black,chinos,slim,all-black,smart|#18181A|solid|#18181A|
IL-005|Pleated Wide Trousers|Charcoal|bottom|Indigo Loom|3199|charcoal,grey,wide-leg,formal,stage,smart|#3A3A3E|solid|#3A3A3E|
IL-006|Slim Chinos|Khaki|bottom|Indigo Loom|2199|khaki,beige,chinos,slim,smart-casual|#B59F78|solid|#B59F78|
IL-007|Corduroy Wide Trousers|Cream|bottom|Indigo Loom|2999|cream,white,corduroy,wide-leg,festive|#E8DCC4|corduroy|#CFC1A5|
KB-001|Court Sneaker|White|footwear|Kerb|3999|white,sneakers,minimal,classic,stage|#F5F5F2|solid|#F5F5F2|
KB-002|Court Sneaker|Black|footwear|Kerb|3999|black,sneakers,all-black,minimal|#1A1A1A|solid|#1A1A1A|
KB-003|City Runner|Signal Red|footwear|Kerb|4499|red,sneakers,sporty,bold|#C62828|solid|#C62828|
KB-004|Penny Loafer|Tan|footwear|Kerb|4999|tan,brown,loafers,smart,festive,formal|#8B5A2B|solid|#8B5A2B|
KB-005|Penny Loafer|Black|footwear|Kerb|4999|black,loafers,formal,all-black,evening|#121212|solid|#121212|
CT-001|Six-Panel Cap|Red|headwear|Cap Theory|899|red,cap,baseball,bold,streetwear|#C8102E|solid|#C8102E|
CT-002|Six-Panel Cap|Black|headwear|Cap Theory|899|black,cap,baseball,all-black|#151515|solid|#151515|
CT-003|BLR Logo Cap|Cream|headwear|Cap Theory|999|cream,white,cap,print,bangalore,bengaluru|#EDE6D6|print|#1F3A5F|BLR
CT-004|Rib Beanie|Charcoal|headwear|Cap Theory|749|charcoal,grey,beanie,winter,casual|#3C3C3C|solid|#3C3C3C|
CT-005|Rib Beanie|Mustard|headwear|Cap Theory|749|yellow,mustard,beanie,bold|#D4A017|solid|#D4A017|
CT-006|Bucket Hat|Olive|headwear|Cap Theory|1099|olive,green,bucket,hat,streetwear|#6B7344|solid|#6B7344|
SH-001|Field Analog|Steel|watch|Second Hand|5499|silver,steel,analog,classic,smart|#C0C0C0|solid|#C0C0C0|
SH-002|Dress Analog|Gold|watch|Second Hand|6999|gold,analog,festive,formal,evening|#C9A227|solid|#C9A227|
SH-003|Retro Digital|Black|watch|Second Hand|2499|black,digital,retro,all-black,casual|#1C1C1C|solid|#1C1C1C|
SH-004|Retro Digital|Silver|watch|Second Hand|2799|silver,digital,retro,tech|#BFC3C7|solid|#BFC3C7|
LL-001|Round Optical|Tortoise|eyewear|Lens Lane|2499|brown,tortoise,glasses,round,classic|#6B4423|solid|#6B4423|
LL-002|Round Optical|Black|eyewear|Lens Lane|2499|black,glasses,round,all-black,classic|#111111|solid|#111111|
LL-003|Wire Round|Gold|eyewear|Lens Lane|2999|gold,glasses,round,metal,festive|#C5A35A|solid|#C5A35A|
LL-004|Stage Shades|Black|eyewear|Lens Lane|1999|black,sunglasses,shades,all-black,bold|#0E0E0E|solid|#0E0E0E|
LL-005|Curb Chain|Silver|neckwear|Lens Lane|1499|silver,chain,metal,streetwear|#C8C8C8|solid|#C8C8C8|
LL-006|Rope Chain|Gold|neckwear|Lens Lane|1799|gold,chain,metal,festive,bangalore|#D4AF37|solid|#D4AF37|`

function parseSnapshot(): P[] {
  return SNAPSHOT.trim().split('\n').map((l) => {
    const [sku, name, colorName, slot, merchant, price, tags, color, pattern, patternColor, printText] = l.split('|')
    return { sku, name, colorName, slot: slot as Slot, merchant, price: Number(price), tags: tags ? tags.split(',') : [], color, pattern, patternColor, printText: printText || '' }
  })
}

let cache: { at: number; products: P[] } | null = null

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
          merchants: { slug: string; name: string }[]
          products: { sku: string; name: string; colorName: string; slot: Slot; merchant: string; price: number; tags: string[]; material: { color: string; pattern: string; patternColor: string; printText: string | null } }[]
        }
        const mn = new Map(j.merchants.map((m) => [m.slug, m.name]))
        const products: P[] = j.products
          .filter((p) => (SLOTS as readonly string[]).includes(p.slot))
          .map((p) => ({
            sku: p.sku, name: p.name, colorName: p.colorName, slot: p.slot, merchant: mn.get(p.merchant) ?? p.merchant,
            price: p.price, tags: p.tags ?? [], color: p.material?.color ?? '#808080', pattern: p.material?.pattern ?? 'solid',
            patternColor: p.material?.patternColor ?? p.material?.color ?? '#808080', printText: p.material?.printText ?? '',
          }))
        if (products.length) {
          cache = { at: Date.now(), products }
          return products
        }
      }
    }
  } catch {
    // use the snapshot
  }
  const products = parseSnapshot()
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

const SYSTEM = `You are the stage check for Hrishikesh's look: he presents on stage at the Bluehost event in Bangalore, in front of a big LED wall, under warm spotlights, on a livestream. You get numbers computed in code and the outfit. Judge how the look will read on stage and on camera.

Guide:
- topContrast is the WCAG contrast of his front garment (outerwear if worn, else top) against the LED wall colour: 4.5 or more pops, 3 to 4.5 is fine, under 3 he melts into the screen.
- brightnessUnderSpots is mean relative luminance of the garments under the spots: 0.1 to 0.6 is balanced, under 0.08 detail disappears on camera, over 0.7 risks glare.
- printReadability is the contrast of any print against its garment (3 or more reads from the back rows); null means no print.
- score: 0 to 100 (85+ stage-ready, 60 to 84 good with a tweak, under 60 risky).
- verdict: one short sentence. note1..note3: three different one-line observations (under 22 words each), concrete and warm, like a stylist backstage.
- swap: the single catalog item, in the same slot as the piece it replaces, that most improves the stage read (usually contrast against the LED wall, e.g. a lighter top or layer against a dark wall). Use the c= value (its contrast vs this LED wall). Mention the store in why. Use null if the look is already strong.
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
  const led = typeof m.ledWallColor === 'string' && /^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(m.ledWallColor) ? (m.ledWallColor.startsWith('#') ? m.ledWallColor : `#${m.ledWallColor}`) : null
  if (!led || num(m.topContrast) === null || num(m.brightnessUnderSpots) === null) return send(res, 400, { error: 'metrics need ledWallColor, topContrast, brightnessUnderSpots' })

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
  }
  const outfit = SLOTS.map((s) => {
    const p = look[s] ? bySku.get(look[s] as string) : undefined
    return `${s}: ${p ? `${p.sku} ${p.name}, ${p.colorName} ${p.color}${p.pattern !== 'solid' ? ` (${p.pattern})` : ''}${p.printText ? ` print "${p.printText}"` : ''}, ${p.merchant}` : 'empty'}`
  }).join('\n')
  const options = products
    .filter((p) => look[p.slot] !== p.sku && (p.slot === 'top' || p.slot === 'outerwear' || p.slot === 'bottom' || look[p.slot]))
    .map((p) => `${p.sku}|${p.slot}|${p.name}|${p.colorName}|${p.merchant}|c=${contrast(p.color, led)}`)
    .join('\n')
  const user = `Metrics: ${JSON.stringify(metrics)}\n\nOutfit:\n${outfit}\n\nSwap options (sku|slot|name|colour|store|contrast vs LED wall):\n${options}`

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
  if (isObj(d.swap) && typeof d.swap.sku === 'string') {
    const p = bySku.get(d.swap.sku)
    if (p && p.slot === d.swap.slot && look[p.slot] !== p.sku) swap = { slot: p.slot, sku: p.sku, why: typeof d.swap.why === 'string' ? d.swap.why.trim().slice(0, 240) : '' }
  }
  return send(res, 200, {
    score: Math.round(Math.max(0, Math.min(100, score))),
    verdict: d.verdict.trim().slice(0, 160),
    notes,
    swap,
    source: 'ai',
    model: out.model,
    ms: Date.now() - t0,
  })
}
