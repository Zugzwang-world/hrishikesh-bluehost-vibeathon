import { CanvasTexture, SRGBColorSpace } from 'three'
import { LED_WALL_COLOR, LED_WALL_COLOR_2, SPEAKER, TALK_TITLE } from './anchors'

let tex: CanvasTexture | null = null
let texGltf: CanvasTexture | null = null

/** Same canvas with flipY=false for glTF UVs. */
export function ledTextureGltf(): CanvasTexture {
  if (texGltf) return texGltf
  texGltf = ledTexture().clone()
  texGltf.flipY = false
  texGltf.needsUpdate = true
  return texGltf
}

function draw(c: HTMLCanvasElement) {
  const W = c.width, H = c.height
  const g = c.getContext('2d')!
  const bg = g.createLinearGradient(0, 0, W, 0)
  bg.addColorStop(0, LED_WALL_COLOR)
  bg.addColorStop(1, LED_WALL_COLOR_2)
  g.fillStyle = bg
  g.fillRect(0, 0, W, H)
  const vg = g.createRadialGradient(W / 2, H / 2, H * 0.2, W / 2, H / 2, W * 0.7)
  vg.addColorStop(0, 'rgba(255,255,255,0.10)'); vg.addColorStop(1, 'rgba(0,0,30,0.35)')
  g.fillStyle = vg; g.fillRect(0, 0, W, H)
  // outlined-square motif
  g.strokeStyle = 'rgba(255,255,255,0.16)'; g.lineWidth = 3
  const step = 128
  for (let x = step / 2; x < W; x += step) for (let y = step / 2; y < H; y += step) {
    const s = ((x * 7 + y * 13) % 5) < 2 ? 56 : 30
    g.strokeRect(x - s / 2, y - s / 2, s, s)
  }
  const font = `'Anton', 'Impact', 'Arial Narrow', system-ui, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillStyle = '#ffffff'
  g.shadowColor = 'rgba(200,210,255,0.9)'; g.shadowBlur = 36
  let size = 230
  g.font = `400 ${size}px ${font}`
  while (g.measureText(SPEAKER).width > W * 0.88 && size > 40) { size -= 8; g.font = `400 ${size}px ${font}` }
  g.fillText(SPEAKER, W / 2, H * 0.22) // high on the wall: clear of his head in every framing
  g.shadowBlur = 0
  let s2 = 58
  g.font = `600 ${s2}px 'Inter', system-ui, sans-serif`
  while (g.measureText(TALK_TITLE).width > W * 0.86 && s2 > 20) { s2 -= 2; g.font = `600 ${s2}px 'Inter', system-ui, sans-serif` }
  g.fillStyle = 'rgba(243,238,230,0.92)'
  g.fillText(TALK_TITLE, W / 2, H * 0.39)
}

/** Wide canvas for the LED wall: cobalt-to-violet wash, outlined squares, speaker name and talk line. Text only. */
export function ledTexture(): CanvasTexture {
  if (tex) return tex
  const c = document.createElement('canvas')
  c.width = 2304; c.height = 960 // 2.4 : 1, the main LED wall's aspect
  draw(c)
  tex = new CanvasTexture(c)
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 8
  // redraw once web fonts (Anton, Inter) are ready
  try {
    document.fonts?.load(`400 64px 'Anton'`).then(() => document.fonts.ready).then(() => {
      draw(c)
      if (tex) tex.needsUpdate = true
      if (texGltf) { texGltf.image = c; texGltf.needsUpdate = true }
    }).catch(() => {})
  } catch { /* ignore */ }
  return tex
}
