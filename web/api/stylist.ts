// Vercel Node function: POST /api/stylist (Lane D2). AI stylist over the merchant catalog, structured output.
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

// ---- /api/stylist ----
// In: { prompt, event, currentLook }  Out: { title, look (all 8 slots), notes [{sku, why}], stageNotes, source: 'ai' }

const DEMO_PROMPT = "I'm presenting on stage at the Bluehost AI Builder Tour today, keep my baggy-jeans vibe, give me a white shirt and a red cap"

function systemPrompt(products: P[]): string {
  const bySlot = SLOTS.map((slot) => {
    const rows = products
      .filter((p) => p.slot === slot)
      .map((p) => [p.sku, p.name, p.colorName, p.merchant, p.price, p.tags.join(','), p.condition, p.size, p.era, p.oneOfOne ? '1of1' : ''].join('|'))
    return `## ${slot}\n${rows.join('\n')}`
  }).join('\n')
  const defaults = slotMap(defaultLookSkus, products)
  const readyLook = slotMap(stageReady.skus, products)
  const persona = SLOTS.map((s) => `${s}: ${defaults[s] ?? 'empty'}`).join(', ')
  const ready = SLOTS.map((s) => `"${s}": ${readyLook[s] ? `"${readyLook[s]}"` : 'null'}`).join(', ')
  return `You are a sharp, warm thrift stylist for Hrishikesh. He is presenting on stage at the Bluehost AI Builder Tour in Bengaluru: an LED wall and a stage wash that runs from cobalt (${STAGE_WASH.cobalt}) to ultraviolet (${STAGE_WASH.ultraviolet}), warm key spots, livestream cameras. You dress him only from the catalog below: one-of-one pieces from five Instagram thrift stores in Bengaluru (Kaapi Thrift, Stonewash Society, Kerbside Kicks, Lids & Lenses, Second Hand), which combine into one look.

Rules:
- Return all 8 slots: top, outerwear, bottom, footwear, headwear, eyewear, watch, neckwear. Use only SKUs listed under that slot, or null to leave a slot empty. top, bottom and footwear are always filled.
- Start from the current look and change what the request asks for; keep the rest unless it clashes. If the request is vague, style a complete look for the occasion.
- House rules: LL-006 (thin gold hex frames) are his real glasses, so eyewear stays LL-006 unless he asks for shades (then LL-007). "white shirt" means KT-001, "red cap" means LL-001, baggy jeans means SW-001. When he is presenting or on stage, add the KT-006 beige linen overshirt and the SH-001 gold digital watch.
- notes: one line each (under 22 words) for the pieces you picked or changed, at most 5. Each names the store and that the piece is 1 of 1, and says why it works.
- title: 2 to 4 words. stageNotes: one sentence on how the look reads under the cobalt-to-ultraviolet wash and on camera.
- Voice: a thrift stylist who knows every rail: confident, specific, warm; speak to Hrishikesh as "you". No emojis.

Worked example.
Current look: ${persona}
Request: "${DEMO_PROMPT}"
Answer: {"title": "${stageReady.title}", "look": {${ready}}, "notes": [{"sku": "KT-001", "why": "Kaapi Thrift's white Oxford, 1 of 1: crisp and bright, it lifts you off the cobalt wash."}, {"sku": "LL-001", "why": "Lids & Lenses red six-panel, 1 of 1: the pop of colour you asked for, readable from the back row."}, {"sku": "SW-001", "why": "Stonewash Society light-wash baggy jeans, 1 of 1: your vibe, kept."}], "stageNotes": "White and beige read bright against the cobalt-to-ultraviolet wash, and the red cap gives the cameras a focal point."}

Catalog (sku|name|colour|store|price INR|tags|condition|size|era|1of1):
${bySlot}`
}

function stylistSchema(products: P[]): Record<string, unknown> {
  const lookProps: Record<string, unknown> = {}
  for (const slot of SLOTS) {
    const skus = products.filter((p) => p.slot === slot).map((p) => p.sku)
    const str = { type: 'string', enum: skus }
    lookProps[slot] = REQUIRED.includes(slot) || !skus.length ? (skus.length ? str : { type: 'null' }) : { anyOf: [str, { type: 'null' }] }
  }
  return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      look: { type: 'object', properties: lookProps, required: [...SLOTS], additionalProperties: false },
      notes: {
        type: 'array',
        items: {
          type: 'object',
          properties: { sku: { type: 'string', enum: products.map((p) => p.sku) }, why: { type: 'string' } },
          required: ['sku', 'why'],
          additionalProperties: false,
        },
      },
      stageNotes: { type: 'string' },
    },
    required: ['title', 'look', 'notes', 'stageNotes'],
    additionalProperties: false,
  }
}

function validLook(raw: unknown, products: P[]): Partial<Record<Slot, string | null>> {
  const bySku = new Map(products.map((p) => [p.sku, p]))
  const out: Partial<Record<Slot, string | null>> = {}
  if (!isObj(raw)) return out
  for (const slot of SLOTS) {
    const v = raw[slot]
    if (typeof v === 'string' && bySku.get(v)?.slot === slot) out[slot] = v
    else if (v === null) out[slot] = null
  }
  return out
}

// House rules, mirrored from web/src/api/stylist.ts so the model and the keyword fallback land the same demo look.
function normText(s: string): string {
  const t = (s || '').toLowerCase().replace(/&/g, ' and ').replace(/off-white/g, 'offwhite').replace(/t-shirt/g, 'tshirt').replace(/[^a-z0-9\s]/g, ' ')
  return ` ${t.split(/\s+/).filter(Boolean).join(' ')} `
}
const PINS: { re: RegExp; slot: Slot; sku: string; why: string }[] = [
  { re: /\bwhite (oxford )?shirt\b/, slot: 'top', sku: 'KT-001', why: 'the crisp white Oxford you asked for' },
  { re: /\bred (six panel )?cap\b/, slot: 'headwear', sku: 'LL-001', why: 'the red cap you asked for' },
  { re: /\bbaggy\b|\bmy jeans\b|\bjeans vibe\b/, slot: 'bottom', sku: 'SW-001', why: 'keeps your baggy-jeans vibe' },
]
const STAGE_RE = /\b(stage|presenting|present|presentation|keynote|talk|speaker|speech|conference|tour)\b/
const SHADES_RE = /\b(shades|sunglasses|sunnies)\b/
const negated = (text: string, words: string) => new RegExp(`\\b(no|without|skip|drop|lose|remove|ditch) (the |my )?(${words})\\b`).test(text)

function applyHouseRules(text: string, has: (sku: string) => boolean, set: (slot: Slot, sku: string, why: string) => void): boolean {
  for (const pin of PINS) if (pin.re.test(text) && has(pin.sku)) set(pin.slot, pin.sku, pin.why)
  const stage = STAGE_RE.test(text)
  if (stage) {
    // Only when he did not name a layer or a watch himself ("blazer for my keynote" keeps the blazer).
    if (!/\b(overshirt|layer|jacket|coat|blazer|blazers|suit|outerwear)\b/.test(text) && has('KT-006')) set('outerwear', 'KT-006', 'a light linen layer that frames you on stage')
    if (!/\bwatch(es)?\b/.test(text) && has('SH-001')) set('watch', 'SH-001', 'a gold digital watch that catches the spots')
  }
  if (SHADES_RE.test(text) && has('LL-007')) set('eyewear', 'LL-007', 'the shades you asked for')
  else if (!negated(text, 'glasses|specs|frames|eyewear') && has('LL-006')) set('eyewear', 'LL-006', 'your own gold hex frames stay on')
  return stage
}

export default async function handler(req: Req, res: ServerResponse) {
  if (preflight(req, res)) return
  const t0 = Date.now()
  let body: unknown
  try {
    body = await readBody(req)
  } catch {
    return send(res, 400, { error: 'invalid JSON' })
  }
  if (!isObj(body)) return send(res, 400, { error: 'body must be an object' })
  const prompt = typeof body.prompt === 'string' ? body.prompt.trim() : ''
  const event = typeof body.event === 'string' ? body.event.trim().slice(0, 200) : ''
  if (!prompt && !event) return send(res, 400, { error: 'prompt is required' })
  if (prompt.length > 1000) return send(res, 400, { error: 'prompt too long' })
  if (body.currentLook !== undefined && body.currentLook !== null && !isObj(body.currentLook)) return send(res, 400, { error: 'currentLook must be an object' })

  const products = await loadCatalog(req)
  const bySku = new Map(products.map((p) => [p.sku, p]))
  const current = validLook(body.currentLook, products)
  const currentLines = SLOTS.map((s) => {
    const p = current[s] ? bySku.get(current[s] as string) : undefined
    return `${s}: ${p ? `${p.sku} ${p.name} (${p.colorName}, ${p.merchant})` : 'empty'}`
  }).join('\n')
  const user = `Occasion: ${event || 'On stage, Bluehost AI Builder Tour, Bengaluru'}\nCurrent look:\n${currentLines}\n\nRequest: ${prompt || 'Style me for the occasion.'}`

  const key = JSON.stringify([prompt.toLowerCase(), event, current])
  const hit = memoGet(key)
  if (hit) return send(res, 200, { ...hit, cached: true, ms: Date.now() - t0 })

  let out: { data: unknown; model: string }
  try {
    out = await callWithRetry(systemPrompt(products), user, stylistSchema(products), 900)
  } catch (e) {
    console.error('stylist failed:', errText(e))
    return send(res, 502, { error: errText(e) })
  }

  const data = isObj(out.data) ? out.data : {}
  const picked = validLook(data.look, products)
  const look = {} as Record<Slot, string | null>
  for (const slot of SLOTS) look[slot] = picked[slot] ?? null
  const defaults = slotMap(defaultLookSkus, products)
  for (const slot of REQUIRED) {
    if (look[slot]) continue
    const d = defaults[slot]
    look[slot] = current[slot] ?? (d && bySku.get(d)?.slot === slot ? d : null) ?? products.find((p) => p.slot === slot)?.sku ?? null
  }

  let notes = (Array.isArray(data.notes) ? data.notes : [])
    .filter((n): n is { sku: string; why: string } => isObj(n) && typeof n.sku === 'string' && typeof n.why === 'string')
    .map((n) => ({ sku: n.sku, why: n.why.trim().slice(0, 240) }))

  // House rules on top of the model: guarantees the demo picks even if the model drifts.
  const guarded: string[] = []
  const stage = applyHouseRules(normText(prompt), (sku) => bySku.has(sku), (slot, sku, why) => {
    if (look[slot] === sku) return
    look[slot] = sku
    guarded.push(slot)
    const p = bySku.get(sku)!
    if (!notes.some((n) => n.sku === sku)) notes.push({ sku, why: `${p.name} from ${p.merchant}${p.oneOfOne ? ', 1 of 1' : ''}: ${why}.` })
  })
  const worn = new Set(Object.values(look).filter(Boolean))
  notes = notes.filter((n) => worn.has(n.sku)).slice(0, 7)
  const readyLook = slotMap(stageReady.skus, products)
  const isStageReady = Object.keys(readyLook).length > 0 && SLOTS.every((s) => !readyLook[s] || look[s] === readyLook[s])

  const result = {
    title: stage && isStageReady ? stageReady.title : typeof data.title === 'string' && data.title.trim() ? data.title.trim().slice(0, 80) : 'Your look',
    look,
    notes,
    stageNotes: typeof data.stageNotes === 'string' ? data.stageNotes.trim().slice(0, 400) : '',
    source: 'ai',
    model: out.model,
    catalog: catalogSource,
    guarded,
  }
  memoSet(key, result)
  return send(res, 200, { ...result, ms: Date.now() - t0 })
}
