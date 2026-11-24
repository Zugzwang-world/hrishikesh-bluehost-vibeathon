// Photoreal cutout of Hrishikesh (fal renders, one per look) as a camera-facing billboard on the stage.
// /looks/index.json lists the renders; missing index or texture -> the toy avatar stays (see Avatar.tsx).
import { useEffect, useMemo, useRef, useState } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { AdditiveBlending, CanvasTexture, Color, Group, Mesh, MeshBasicMaterial, SRGBColorSpace, Texture, TextureLoader } from 'three'
import { REQUIRED, SLOTS } from '../config'
import type { Catalog, Look } from '../api/types'
import { PARAMS } from '../lib/params'
import { useStore } from '../store'
import { clamp01, live } from './anchors'
import { stageFx } from './Stage'
import { markSettled } from './ready'

export type LookEntry = { key: string; skus: string[]; title: string | null; src: string }
export type LooksIndex = { version: number; caption: string; canvas: { w: number; h: number; figurePx: number; feetY: number }; looks: LookEntry[] }

// plane size in metres from the normalised canvas (1300 px figure = 1.75 m)
const PLANE = { w: 1.077, h: 1.885, bottom: -0.027 }

let indexPromise: Promise<LooksIndex | null> | null = null
export function loadLooksIndex(): Promise<LooksIndex | null> {
  if (PARAMS.avatar === 'toy' || PARAMS.mode === 'product') return Promise.resolve(null)
  if (!indexPromise) {
    indexPromise = fetch('/looks/index.json', { cache: 'no-cache' })
      .then(r => (r.ok && (r.headers.get('content-type') || '').includes('json') ? r.json() : null))
      .then((j: LooksIndex | null) => (j && Array.isArray(j.looks) && j.looks.length ? j : null))
      .catch(() => null)
  }
  return indexPromise
}

export const lookKey = (look: Look) => (Object.values(look).filter(Boolean) as string[]).sort().join(',')

/** Exact render for the look, else the nearest (most shared SKUs; tie -> shares top/bottom/footwear). */
export function resolveLook(index: LooksIndex, look: Look, catalog: Catalog | null): { entry: LookEntry; exact: boolean } {
  const key = lookKey(look)
  const exact = index.looks.find(l => l.key === key)
  if (exact) return { entry: exact, exact: true }
  const worn = new Set(Object.values(look).filter(Boolean) as string[])
  const req = new Set(REQUIRED.map(s => look[s]).filter(Boolean) as string[])
  let best = index.looks[0], bestScore = -1
  for (const l of index.looks) {
    let shared = 0, sharedReq = 0
    for (const s of l.skus) { if (worn.has(s)) shared++; if (req.has(s)) sharedReq++ }
    const extra = l.skus.length - shared // pieces he'd be shown wearing that aren't in the look
    const score = shared * 100 + sharedReq * 10 - extra
    if (score > bestScore) { bestScore = score; best = l }
  }
  void catalog; void SLOTS
  return { entry: best, exact: false }
}

const loader = new TextureLoader()
const texCache = new Map<string, Promise<Texture>>()
function loadTexture(src: string): Promise<Texture> {
  let p = texCache.get(src)
  if (!p) {
    p = new Promise<Texture>((res, rej) => loader.load(src, t => { t.colorSpace = SRGBColorSpace; t.anisotropy = 8; res(t) }, undefined, rej))
    texCache.set(src, p)
    p.catch(() => texCache.delete(src))
  }
  return p
}

/** 'pending' until we know; 'cutout' once the first render texture is in; 'toy' on any failure or avatar=toy. */
export function useCutoutMode(): 'pending' | 'cutout' | 'toy' {
  const [mode, setMode] = useState<'pending' | 'cutout' | 'toy'>(PARAMS.avatar === 'toy' ? 'toy' : 'pending')
  useEffect(() => {
    if (PARAMS.avatar === 'toy') return
    let live = true
    // Slow network: show the toy figure after 6 s, but keep loading and switch to the cutout when it arrives.
    const timer = window.setTimeout(() => { if (live) setMode(m => (m === 'pending' ? 'toy' : m)) }, 6000)
    loadLooksIndex().then(async idx => {
      if (!idx) { if (live) setMode('toy'); return }
      const st = useStore.getState()
      // wait briefly for the catalog/look so the first texture is the right one
      for (let i = 0; i < 30 && !st.catalog && !useStore.getState().catalog; i++) await new Promise(r => setTimeout(r, 100))
      const s = useStore.getState()
      const { entry } = resolveLook(idx, s.look, s.catalog)
      try { await loadTexture(entry.src); if (live) setMode('cutout') } catch { if (live) setMode('toy') }
    })
    return () => { live = false; clearTimeout(timer) }
  }, [])
  return mode
}

function blobTexture(): CanvasTexture {
  const c = document.createElement('canvas'); c.width = c.height = 128
  const g = c.getContext('2d')!
  const r = g.createRadialGradient(64, 64, 4, 64, 64, 62)
  r.addColorStop(0, 'rgba(0,0,0,0.75)'); r.addColorStop(0.55, 'rgba(0,0,0,0.35)'); r.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = r; g.fillRect(0, 0, 128, 128)
  return new CanvasTexture(c)
}

const WHITE = new Color(1, 1, 1)
const WASH = new Color(0.84, 0.88, 1.06) // cobalt/violet stage wash, light enough to keep the face readable
const RIM = new Color('#5b4dff')

/** The billboard: two layers for a ~400 ms crossfade with a shimmer, a rim glow, and a soft floor shadow. */
export function Cutout() {
  const camera = useThree(s => s.camera)
  const look = useStore(s => s.look)
  const catalog = useStore(s => s.catalog)
  const set = useStore(s => s.set)
  const group = useRef<Group>(null)
  const meshA = useRef<Mesh>(null), meshB = useRef<Mesh>(null), rimRef = useRef<Mesh>(null), blobRef = useRef<Mesh>(null)
  const mats = useMemo(() => ({
    a: new MeshBasicMaterial({ transparent: true, alphaTest: 0.02, toneMapped: false, depthWrite: true }),
    b: new MeshBasicMaterial({ transparent: true, alphaTest: 0.02, toneMapped: false, depthWrite: false, opacity: 0 }),
    rim: new MeshBasicMaterial({ transparent: true, blending: AdditiveBlending, depthWrite: false, toneMapped: false, color: RIM, opacity: 0.4 }),
    blob: new MeshBasicMaterial({ transparent: true, depthWrite: false, map: blobTexture(), opacity: 0.55 }),
  }), [])
  const fade = useRef({ t0: -1, active: false })
  const [index, setIndex] = useState<LooksIndex | null>(null)
  const shown = useRef<string>('')

  useEffect(() => { loadLooksIndex().then(setIndex) }, [])

  useEffect(() => {
    if (!index) return
    const { entry, exact } = resolveLook(index, look, catalog)
    set({ cutoutCaption: index.caption || 'AI render of Hrishikesh', cutoutExact: exact })
    if (entry.src === shown.current) return
    let live = true
    loadTexture(entry.src).then(tex => {
      if (!live) return
      if (!shown.current) {
        mats.a.map = tex; mats.a.needsUpdate = true; mats.rim.map = tex; mats.rim.needsUpdate = true
        markSettled('avatar'); markSettled('wardrobe')
      } else {
        mats.b.map = tex; mats.b.needsUpdate = true
        fade.current = { t0: performance.now(), active: true }
      }
      shown.current = entry.src
    }).catch(() => { /* keep the current render */ })
    return () => { live = false }
  }, [index, look, catalog, mats, set])

  useEffect(() => () => set({ cutoutCaption: null, cutoutExact: true }), [set])

  useFrame(({ clock }) => {
    const g = group.current
    if (!g) return
    g.position.copy(live.avatar)
    // cylindrical billboard: face the camera around Y, with a tiny breathing sway
    const yaw = Math.atan2(camera.position.x - g.position.x, camera.position.z - g.position.z)
    g.rotation.y = yaw + Math.sin(clock.elapsedTime * 0.6) * 0.035
    // stage wash
    const k = clamp01(stageFx.mix)
    let flash = 0
    const f = fade.current
    if (f.active) {
      const t = clamp01((performance.now() - f.t0) / 400)
      mats.b.opacity = t
      mats.a.opacity = 1 - t * 0.999
      flash = Math.sin(t * Math.PI) * 0.22
      if (t >= 1) {
        // promote B to A
        mats.a.map = mats.b.map; mats.a.opacity = 1; mats.a.needsUpdate = true
        mats.rim.map = mats.b.map; mats.rim.needsUpdate = true
        mats.b.opacity = 0
        f.active = false
      }
    }
    mats.a.color.copy(WHITE).lerp(WASH, k).multiplyScalar(1 + flash)
    mats.b.color.copy(mats.a.color)
    mats.rim.opacity = 0.18 + 0.45 * k
  })

  const cy = PLANE.bottom + PLANE.h / 2
  return (
    <group ref={group} name="cutout">
      <mesh ref={blobRef} position={[0, 0.004, 0.02]} rotation={[-Math.PI / 2, 0, 0]} material={mats.blob} renderOrder={1}>
        <planeGeometry args={[0.95, 0.42]} />
      </mesh>
      <mesh ref={rimRef} position={[0, cy + 0.01, -0.02]} scale={[1.045, 1.02, 1]} material={mats.rim} renderOrder={2}>
        <planeGeometry args={[PLANE.w, PLANE.h]} />
      </mesh>
      <mesh ref={meshA} position={[0, cy, 0]} material={mats.a} renderOrder={3}>
        <planeGeometry args={[PLANE.w, PLANE.h]} />
      </mesh>
      <mesh ref={meshB} position={[0, cy, 0.002]} material={mats.b} renderOrder={4}>
        <planeGeometry args={[PLANE.w, PLANE.h]} />
      </mesh>
    </group>
  )
}
