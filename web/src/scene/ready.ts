// 'stage:ready' for the instant poster in index.html: fired once, two frames after the avatar, wardrobe and stage
// (glTF or their primitive fallbacks) are in the scene. Safety nets: 5 s after the first frame, 12 s after boot.
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import meshes from '../contract/meshes.json'
import { assetExists } from './assets'

export type AssetKey = 'avatar' | 'wardrobe' | 'stage'
const settled = new Set<AssetKey>()
let fired = false

export function markSettled(k: AssetKey) { settled.add(k) }
for (const k of ['avatar', 'wardrobe', 'stage'] as AssetKey[]) assetExists(meshes.files[k]).then(ok => { if (!ok) settled.add(k) })

export function fireReady() {
  if (fired) return
  fired = true
  try { window.dispatchEvent(new Event('stage:ready')) } catch { /* ignore */ }
}
if (typeof window !== 'undefined') window.setTimeout(fireReady, 12000)

export function ReadySignal({ need }: { need: AssetKey[] }) {
  const st = useRef({ frames: 0, t0: -1, armed: -1 })
  useFrame(({ clock }) => {
    if (fired) return
    const s = st.current
    if (s.t0 < 0) s.t0 = clock.elapsedTime
    s.frames++
    if (s.armed < 0 && (need.every(k => settled.has(k)) || clock.elapsedTime - s.t0 > 5)) s.armed = s.frames
    if (s.armed >= 0 && s.frames - s.armed >= 2) fireReady()
  })
  return null
}
