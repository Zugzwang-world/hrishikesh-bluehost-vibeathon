import { CanvasTexture, SRGBColorSpace } from 'three'
import { LED_WALL_COLOR, SPEAKER, TALK_TITLE } from './anchors'

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

/** 16:9 canvas for the LED wall: speaker name and talk title. */
export function ledTexture(): CanvasTexture {
  if (tex) return tex
  const W = 1920, H = 1080
  const c = document.createElement('canvas')
  c.width = W; c.height = H
  const g = c.getContext('2d')!
  const bg = g.createLinearGradient(0, 0, W, H)
  bg.addColorStop(0, '#0a1650')
  bg.addColorStop(0.55, LED_WALL_COLOR)
  bg.addColorStop(1, '#0b1a5e')
  g.fillStyle = bg
  g.fillRect(0, 0, W, H)
  // soft light blooms
  const rg = g.createRadialGradient(W * 0.72, H * 0.3, 10, W * 0.72, H * 0.3, W * 0.5)
  rg.addColorStop(0, 'rgba(120,170,255,0.45)'); rg.addColorStop(1, 'rgba(120,170,255,0)')
  g.fillStyle = rg; g.fillRect(0, 0, W, H)
  // grid lines
  g.strokeStyle = 'rgba(255,255,255,0.06)'; g.lineWidth = 2
  for (let x = 0; x < W; x += 80) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke() }
  for (let y = 0; y < H; y += 80) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke() }
  const font = `system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillStyle = 'rgba(255,255,255,0.7)'
  g.font = `600 44px ${font}`
  g.fillText('BLUEHOST  ·  BANGALORE', W / 2, H * 0.28)
  g.fillStyle = '#ffffff'
  g.shadowColor = 'rgba(160,200,255,0.9)'; g.shadowBlur = 40
  let size = 250
  g.font = `900 ${size}px ${font}`
  while (g.measureText(SPEAKER).width > W * 0.86) { size -= 10; g.font = `900 ${size}px ${font}` }
  g.fillText(SPEAKER, W / 2, H * 0.5)
  g.shadowBlur = 0
  g.font = `500 64px ${font}`
  g.fillStyle = '#dfe7ff'
  g.fillText(TALK_TITLE, W / 2, H * 0.7)
  tex = new CanvasTexture(c)
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 8
  return tex
}
