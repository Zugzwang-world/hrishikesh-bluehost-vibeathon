import { Suspense, useRef, useState, type PointerEvent } from 'react'
import { Canvas } from '@react-three/fiber'
import { ContactShadows, PerformanceMonitor } from '@react-three/drei'
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing'
import meshes from '../contract/meshes.json'
import { useStore } from '../store'
import { ANCHORS, turntable } from './anchors'
import { useAssetExists } from './assets'
import { AssetBoundary, Avatar } from './Avatar'
import { CameraRig, GlbStage, Lights, PrimitiveStage } from './Stage'

export const canvasRef: { current: HTMLCanvasElement | null } = { current: null }

export function hasWebGL(): boolean {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false }
}

export function snapshot(name = 'stage-look.png') {
  const c = canvasRef.current
  if (!c) return
  try {
    const a = document.createElement('a')
    a.href = c.toDataURL('image/png')
    a.download = name
    a.click()
  } catch (e) { console.warn('[stage] snapshot failed', e) }
}

function StageSet() {
  const hasStage = useAssetExists(meshes.files.stage)
  const prim = <PrimitiveStage />
  return hasStage ? <AssetBoundary fallback={prim}><Suspense fallback={prim}><GlbStage /></Suspense></AssetBoundary> : prim
}

export default function Scene() {
  const drag = useRef<{ x: number; id: number } | null>(null)
  const [dpr, setDpr] = useState(1.75)
  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    if (useStore.getState().mode !== 'fit') return
    drag.current = { x: e.clientX, id: e.pointerId }
    turntable.dragging = true; turntable.vel = 0; turntable.lastInteract = performance.now()
    ;(e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId)
  }
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    const dx = e.clientX - d.x
    d.x = e.clientX
    turntable.yaw += dx * 0.011
    turntable.vel = dx * 0.011 * 60
    turntable.lastInteract = performance.now()
  }
  const onUp = () => { drag.current = null; turntable.dragging = false; turntable.lastInteract = performance.now() }

  return (
    <div className="scene" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
      <Canvas
        dpr={[1, dpr]}
        gl={{ preserveDrawingBuffer: true, antialias: true, powerPreference: 'high-performance' }}
        camera={{ fov: 30, near: 0.05, far: 80, position: ANCHORS.cam_fit.toArray() }}
        onCreated={({ gl }) => { canvasRef.current = gl.domElement }}
      >
        <PerformanceMonitor factor={1} onChange={({ factor }) => setDpr(Math.round((1 + 0.75 * factor) * 4) / 4)} onFallback={() => setDpr(1)} flipflops={4} />
        <Lights />
        <CameraRig />
        <StageSet />
        <Avatar />
        <ContactShadows position={[0, 0.003, 0.8]} scale={[6, 5]} resolution={384} blur={2.4} opacity={0.55} far={2.2} frames={Infinity} />
        <EffectComposer multisampling={4}>
          <Bloom mipmapBlur intensity={0.55} luminanceThreshold={0.82} luminanceSmoothing={0.2} />
          <Vignette offset={0.28} darkness={0.62} />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
