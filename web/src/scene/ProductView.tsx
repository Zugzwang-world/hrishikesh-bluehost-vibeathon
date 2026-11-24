// /product?sku=SKU : one piece on an invisible mannequin, slow turntable, soft studio light. Transparent background.
import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ContactShadows } from '@react-three/drei'
import { Box3, Group, PerspectiveCamera, Vector3 } from 'three'
import { PARAMS } from '../lib/params'
import { productBySku, useStore } from '../store'
import { GarmentPiece } from './Avatar'

const SMALL = new Set(['watch', 'neckwear', 'eyewear'])

function Rig({ target }: { target: React.RefObject<Group | null> }) {
  const camera = useThree(s => s.camera) as PerspectiveCamera
  const size = useThree(s => s.size)
  const st = useMemo(() => ({ box: new Box3(), c: new Vector3(), s: new Vector3(), aim: new Vector3(0, 1, 0), dist: 3, ready: false, n: 0, a: 0 }), [])
  useFrame(({ clock }, dt) => {
    const g = target.current
    if (!g) return
    // re-measure for the first frames (the glTF may arrive after the primitive)
    if (st.n++ % 20 === 0 && st.n < 400) {
      st.box.setFromObject(g)
      if (!st.box.isEmpty()) {
        st.box.getCenter(st.c); st.box.getSize(st.s)
        const tan = Math.tan((camera.fov * Math.PI) / 360)
        const aspect = size.width / Math.max(1, size.height)
        const h = Math.max(st.s.y, 0.04), w = Math.max(st.s.x, st.s.z, 0.04)
        st.dist = Math.max((h * 0.5) / tan, (w * 0.5) / (tan * aspect)) * 1.55 + Math.max(st.s.z, st.s.x) * 0.5
        st.aim.copy(st.c); st.ready = true
      }
    }
    st.a += dt * 0.45
    if (!st.ready) return
    const t = clock.elapsedTime
    camera.position.set(st.aim.x + Math.sin(st.a) * st.dist, st.aim.y + st.dist * 0.18 + Math.sin(t * 0.5) * st.dist * 0.03, st.aim.z + Math.cos(st.a) * st.dist)
    camera.near = Math.max(0.01, st.dist / 50); camera.updateProjectionMatrix()
    camera.lookAt(st.aim)
  })
  return null
}

function Piece() {
  const catalog = useStore(s => s.catalog)
  const p = productBySku(catalog, PARAMS.sku) ?? catalog?.products[0]
  const ref = useRef<Group>(null)
  if (!p) return null
  return (
    <>
      <group ref={ref} key={p.sku}>
        <GarmentPiece p={p} />
      </group>
      <Rig target={ref} />
      {!SMALL.has(p.slot) && <ContactShadows position={[0, p.slot === 'footwear' ? 0.001 : 0.4, 0]} scale={2} resolution={256} blur={2.5} opacity={0.35} far={2} />}
    </>
  )
}

export default function ProductView() {
  useEffect(() => {
    for (const el of [document.documentElement, document.body, document.getElementById('root')]) if (el) el.style.background = 'transparent'
  }, [])
  return (
    <Canvas dpr={[1, 2]} gl={{ alpha: true, antialias: true, preserveDrawingBuffer: true }} camera={{ fov: 26, position: [0, 1.3, 3] }} style={{ position: 'absolute', inset: 0 }}>
      <hemisphereLight args={['#ffffff', '#d8d2c8', 1.1]} />
      <directionalLight position={[2.5, 4, 3]} intensity={2.2} color="#fffaf2" />
      <directionalLight position={[-3, 2, 2]} intensity={0.9} color="#eef1ff" />
      <directionalLight position={[0, 3, -3]} intensity={1.1} color="#ffffff" />
      <Piece />
    </Canvas>
  )
}
