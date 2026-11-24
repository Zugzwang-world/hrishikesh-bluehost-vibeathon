import { Component, Suspense, useEffect, useLayoutEffect, useMemo, useRef, type ReactNode } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import { Box3, Group, Matrix4, Mesh, MeshStandardMaterial, Object3D, Vector3, type Material } from 'three'
import meshes from '../contract/meshes.json'
import { SLOTS } from '../config'
import type { Product } from '../api/types'
import { productBySku, useStore } from '../store'
import { ANCHORS, clamp01, easeInOutCubic, turntable } from './anchors'
import { DRACO_PATH, useAssetExists } from './assets'
import { garmentMaterial, printTexture } from './materials'
import { PrimitiveBody, PrimitiveGarment } from './Primitives'

type MeshInfo = { slot: string; hides: string[]; shows: string[] }
const MESHES = meshes.meshes as Record<string, MeshInfo>
const AVATAR_URL = meshes.files.avatar
const WARDROBE_URL = meshes.files.wardrobe

class Boundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(e: unknown) { console.warn('[stage] asset fallback', e) }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}
export { Boundary as AssetBoundary }

function useEquipped(): Product[] {
  const look = useStore(s => s.look)
  const catalog = useStore(s => s.catalog)
  return useMemo(() => SLOTS.map(s => productBySku(catalog, look[s])).filter(Boolean) as Product[], [look, catalog])
}

/** Visibility of body regions and hair for the equipped meshes (contract hides/shows). */
function useHidden(items: Product[]) {
  return useMemo(() => {
    const hidden = new Set<string>(meshes.defaultHidden)
    for (const p of items) {
      const info = MESHES[p.mesh]
      if (!info) continue
      for (const h of info.hides) hidden.add(h)
    }
    for (const p of items) for (const s of MESHES[p.mesh]?.shows ?? []) hidden.delete(s)
    return hidden
  }, [items])
}

const easeOutBack = (t: number) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2) }
const _m = new Matrix4()
const _box = new Box3()
const _c = new Vector3()

/** Pop + shimmer when a garment mounts (key it by SKU). */
function Pop({ children }: { children: ReactNode }) {
  const outer = useRef<Group>(null)
  const inner = useRef<Group>(null)
  const t0 = useRef(-1)
  const mats = useRef<MeshStandardMaterial[]>([])
  useLayoutEffect(() => {
    const o = outer.current, i = inner.current
    if (!o || !i) return
    o.position.set(0, 0, 0); i.position.set(0, 0, 0); o.scale.setScalar(0.9)
    o.updateWorldMatrix(true, true)
    _box.setFromObject(i)
    if (!_box.isEmpty() && o.parent) {
      _box.getCenter(_c).applyMatrix4(_m.copy(o.parent.matrixWorld).invert())
      o.position.copy(_c); i.position.copy(_c).multiplyScalar(-1)
    }
    const ms = new Set<MeshStandardMaterial>()
    i.traverse(x => { const m = (x as Mesh).material as MeshStandardMaterial | undefined; if (m && m.isMeshStandardMaterial) ms.add(m) })
    mats.current = [...ms]
    t0.current = -1
  }, [])
  useFrame(({ clock }) => {
    const o = outer.current
    if (!o) return
    if (t0.current < 0) t0.current = clock.elapsedTime
    const t = (clock.elapsedTime - t0.current) / 0.45
    if (t > 1.2) { if (o.scale.x !== 1) { o.scale.setScalar(1); for (const m of mats.current) m.emissiveIntensity = 0 } return }
    const k = clamp01(t)
    o.scale.setScalar(0.9 + 0.1 * easeOutBack(k))
    const glow = (1 - k) * (1 - k) * 0.55
    for (const m of mats.current) { m.emissive.setRGB(1, 1, 1); m.emissiveIntensity = glow }
  })
  return <group ref={outer}><group ref={inner}>{children}</group></group>
}

function PrintPlane({ p, z, y = 1.3, w = 0.22 }: { p: Product; z: number; y?: number; w?: number }) {
  const tex = printTexture(p)
  if (!tex) return null
  return (
    <mesh position={[0, y, z]} renderOrder={2}>
      <planeGeometry args={[w, w / 2]} />
      <meshStandardMaterial map={tex} transparent depthWrite={false} polygonOffset polygonOffsetFactor={-2} roughness={0.9} />
    </mesh>
  )
}
const PRIMITIVE_PRINT_Z: Record<string, number> = { top_tee: 0.1235, top_oversized: 0.136, top_shirt: 0.121 }

function PrimitiveWardrobe({ items }: { items: Product[] }) {
  return (
    <>
      {items.map(p => {
        const m = garmentMaterial(p)
        const print = p.material.printText && PRIMITIVE_PRINT_Z[p.mesh] ? <PrintPlane p={p} z={PRIMITIVE_PRINT_Z[p.mesh]} /> : undefined
        return (
          <Pop key={p.sku}>
            <PrimitiveGarment mesh={p.mesh} m={m} print={print} />
            {p.slot === 'headwear' && p.material.printText && <PrintPlane p={p} z={0.119} y={1.71} w={0.09} />}
          </Pop>
        )
      })}
    </>
  )
}

/** wardrobe.glb: clone the node of each equipped garment, material from the catalog. Missing node -> primitive. */
function GlbWardrobe({ items }: { items: Product[] }) {
  const gltf = useGLTF(WARDROBE_URL, DRACO_PATH)
  const nodes = useMemo(() => {
    gltf.scene.updateMatrixWorld(true)
    const map = new Map<string, Object3D>()
    gltf.scene.traverse(o => { if (!map.has(o.name)) map.set(o.name, o) })
    return map
  }, [gltf])
  return (
    <>
      {items.map(p => {
        const node = nodes.get(p.mesh)
        if (!node) return <Pop key={p.sku}><PrimitiveGarment mesh={p.mesh} m={garmentMaterial(p)} /></Pop>
        return <Pop key={p.sku}><GlbGarment node={node} p={p} /></Pop>
      })}
    </>
  )
}

function GlbGarment({ node, p }: { node: Object3D; p: Product }) {
  const { obj, front } = useMemo(() => {
    const obj = node.clone(true)
    node.matrixWorld.decompose(obj.position, obj.quaternion, obj.scale)
    const m = garmentMaterial(p)
    obj.traverse(o => { const mesh = o as Mesh; if (mesh.isMesh) { mesh.material = m; mesh.castShadow = true; mesh.receiveShadow = true } })
    const box = new Box3().setFromObject(node)
    return { obj, front: box.isEmpty() ? 0.13 : box.max.z }
  }, [node, p])
  const isTop = p.slot === 'top'
  return (
    <>
      <primitive object={obj} />
      {p.material.printText && isTop && <PrintPlane p={p} z={front + 0.004} y={1.28} />}
      {p.material.printText && p.slot === 'headwear' && <PrintPlane p={p} z={front - 0.02} y={1.71} w={0.09} />}
    </>
  )
}

/** avatar.glb with contract visibility. */
function GlbBody({ hidden }: { hidden: Set<string> }) {
  const gltf = useGLTF(AVATAR_URL, DRACO_PATH)
  const named = useMemo(() => {
    const list: Object3D[] = []
    gltf.scene.traverse(o => {
      const mesh = o as Mesh
      if (mesh.isMesh) { mesh.castShadow = true; mesh.receiveShadow = true }
      if (o.name.startsWith('body_') || o.name.startsWith('hair_')) list.push(o)
    })
    return list
  }, [gltf])
  useLayoutEffect(() => { for (const o of named) o.visible = !hidden.has(o.name) }, [named, hidden])
  return <primitive object={gltf.scene} />
}

function useSkin() {
  return useMemo(() => ({
    skin: new MeshStandardMaterial({ color: '#9b6e53', roughness: 0.62 }) as Material,
    hair: new MeshStandardMaterial({ color: '#17120f', roughness: 0.9 }) as Material,
  }), [])
}

/** The avatar root: turntable in fitting mode, glide to the centre mark in showtime. */
export function Avatar() {
  const items = useEquipped()
  const hidden = useHidden(items)
  const { skin, hair } = useSkin()
  const hasAvatar = useAssetExists(AVATAR_URL)
  const hasWardrobe = useAssetExists(WARDROBE_URL)
  const root = useRef<Group>(null)
  // swing the avatar to face the camera whenever the look changes
  const first = useRef(true)
  useEffect(() => { if (first.current) { first.current = false; return } turntable.faceAt = performance.now() }, [items])
  const st = useRef({ mode: 'fit', t0: 0, fromYaw: 0, toYaw: 0, from: new Vector3().copy(ANCHORS.avatar_fit) })

  useFrame(({ clock }, dt) => {
    const g = root.current
    if (!g) return
    const { mode, showStart } = useStore.getState()
    const s = st.current
    const now = clock.elapsedTime
    if (mode !== s.mode) {
      s.mode = mode; s.t0 = now; s.from.copy(g.position); s.fromYaw = turntable.yaw
      const twoPi = Math.PI * 2
      s.toYaw = mode === 'show' ? Math.ceil(turntable.yaw / twoPi) * twoPi + twoPi : turntable.yaw
    }
    const t = now - s.t0
    if (mode === 'show') {
      void showStart
      const k = easeInOutCubic(clamp01((t - 0.25) / 2.4))
      g.position.lerpVectors(s.from, ANCHORS.mark_center, k)
      turntable.yaw = s.fromYaw + (s.toYaw - s.fromYaw) * k + (k >= 1 ? Math.sin(t * 0.6) * 0.12 : 0)
    } else {
      const k = easeInOutCubic(clamp01(t / 1.2))
      g.position.lerpVectors(s.from, ANCHORS.avatar_fit, k)
      if (!turntable.dragging) {
        const pnow = performance.now()
        if (pnow - turntable.faceAt < 1500) {
          const twoPi = Math.PI * 2
          const target = Math.round(turntable.yaw / twoPi) * twoPi
          turntable.yaw += (target - turntable.yaw) * Math.min(1, dt * 5)
          turntable.vel = 0
          turntable.lastInteract = pnow
        } else {
          turntable.vel *= Math.pow(0.04, dt)
          const idle = pnow - turntable.lastInteract > 2200
          turntable.yaw += (turntable.vel + (idle ? 0.22 : 0)) * dt
        }
      }
    }
    g.rotation.y = turntable.yaw
  })

  const prim = <PrimitiveBody skin={skin} hair={hair} hidden={hidden} />
  const primWardrobe = <PrimitiveWardrobe items={items} />
  return (
    <group ref={root} position={ANCHORS.avatar_fit.toArray()} name="avatar_root">
      {hasAvatar ? <Boundary fallback={prim}><Suspense fallback={prim}><GlbBody hidden={hidden} /></Suspense></Boundary> : prim}
      {hasWardrobe ? <Boundary fallback={primWardrobe}><Suspense fallback={primWardrobe}><GlbWardrobe items={items} /></Suspense></Boundary> : primWardrobe}
    </group>
  )
}
