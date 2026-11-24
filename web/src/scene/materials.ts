import { CanvasTexture, Color, MeshStandardMaterial, RepeatWrapping, SRGBColorSpace, type Texture } from 'three'
import type { Product } from '../api/types'

const cache = new Map<string, MeshStandardMaterial>()
const printCache = new Map<string, CanvasTexture>()
const SIZE = 256

function proceduralMask(ctx: CanvasRenderingContext2D, pattern: string) {
  // white = patternColor, black = base color
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, SIZE, SIZE)
  ctx.fillStyle = '#fff'
  if (pattern === 'stripe') {
    for (let y = 0; y < SIZE; y += 32) ctx.fillRect(0, y, SIZE, 12)
  } else if (pattern === 'check') {
    ctx.globalAlpha = 0.55
    for (let i = 0; i < SIZE; i += 64) { ctx.fillRect(i, 0, 22, SIZE); ctx.fillRect(0, i, SIZE, 22) }
    ctx.globalAlpha = 0.9
    for (let i = 40; i < SIZE; i += 64) { ctx.fillRect(i, 0, 3, SIZE); ctx.fillRect(0, i, SIZE, 3) }
    ctx.globalAlpha = 1
  } else if (pattern === 'denim') {
    ctx.globalAlpha = 0.35
    for (let i = -SIZE; i < SIZE * 2; i += 6) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + SIZE, SIZE); ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke() }
    ctx.globalAlpha = 1
  } else if (pattern === 'melange') {
    for (let i = 0; i < 2600; i++) { ctx.globalAlpha = Math.random() * 0.6; ctx.fillRect(Math.random() * SIZE, Math.random() * SIZE, 2, 1) }
    ctx.globalAlpha = 1
  } else if (pattern === 'corduroy') {
    for (let x = 0; x < SIZE; x += 8) { const g = ctx.createLinearGradient(x, 0, x + 8, 0); g.addColorStop(0, '#000'); g.addColorStop(0.5, 'rgba(255,255,255,0.5)'); g.addColorStop(1, '#000'); ctx.fillStyle = g; ctx.fillRect(x, 0, 8, SIZE) }
  }
}

function compose(canvas: HTMLCanvasElement, base: string, over: string, maskSrc: CanvasImageSource | null, pattern: string) {
  const ctx = canvas.getContext('2d')!
  if (maskSrc) ctx.drawImage(maskSrc, 0, 0, SIZE, SIZE)
  else proceduralMask(ctx, pattern)
  const img = ctx.getImageData(0, 0, SIZE, SIZE)
  const a = new Color(base), b = new Color(over)
  const ar = a.r * 255, ag = a.g * 255, ab = a.b * 255, br = b.r * 255, bg = b.g * 255, bb = b.b * 255
  const d = img.data
  for (let i = 0; i < d.length; i += 4) {
    const m = d[i] / 255
    d[i] = ar + (br - ar) * m; d[i + 1] = ag + (bg - ag) * m; d[i + 2] = ab + (bb - ab) * m; d[i + 3] = 255
  }
  ctx.putImageData(img, 0, 0)
}

function patternTexture(p: Product): Texture {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = SIZE
  const { color, patternColor, pattern } = p.material
  const over = patternColor || '#ffffff'
  compose(canvas, color, over, null, pattern)
  const tex = new CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = RepeatWrapping
  tex.repeat.set(4, 4)
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 4
  // upgrade to Lane E's grayscale mask when present
  const img = new Image()
  img.onload = () => { try { compose(canvas, color, over, img, pattern); tex.needsUpdate = true } catch { /* keep procedural */ } }
  img.src = `/textures/${pattern}.png`
  return tex
}

export function garmentMaterial(p: Product): MeshStandardMaterial {
  let m = cache.get(p.sku)
  if (m) return m
  const { color, pattern, roughness, metalness } = p.material
  const tiled = pattern !== 'solid' && pattern !== 'print'
  m = new MeshStandardMaterial({
    color: tiled ? '#ffffff' : color,
    roughness: roughness ?? 0.8,
    metalness: metalness ?? 0,
    map: tiled ? patternTexture(p) : null,
  })
  m.name = 'garment_' + p.sku
  cache.set(p.sku, m)
  return m
}

/** Transparent canvas with the product's print text, for a chest decal. */
export function printTexture(p: Product): CanvasTexture | null {
  const text = p.material.printText
  if (!text) return null
  let t = printCache.get(p.sku)
  if (t) return t
  const c = document.createElement('canvas')
  c.width = 512; c.height = 256
  const ctx = c.getContext('2d')!
  ctx.clearRect(0, 0, 512, 256)
  ctx.fillStyle = p.material.patternColor || '#111111'
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  let size = 150
  ctx.font = `900 ${size}px system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif`
  while (ctx.measureText(text).width > 470 && size > 30) { size -= 6; ctx.font = `900 ${size}px system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif` }
  ctx.fillText(text, 256, 132)
  t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  printCache.set(p.sku, t)
  return t
}
