import { useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import {
  AdditiveBlending, Color, DirectionalLight, FrontSide, HemisphereLight, AmbientLight, Mesh, MeshBasicMaterial,
  MeshStandardMaterial, Object3D, PerspectiveCamera, Quaternion, SpotLight, Vector3, WebGLRenderTarget, type Material,
} from 'three'
import meshes from '../contract/meshes.json'
import { useStore } from '../store'
import { PARAMS } from '../lib/params'
import { ANCHORS, clamp01, easeInOutCubic, live, REDUCED_MOTION, type AnchorName } from './anchors'
import { DRACO_PATH } from './assets'
import { ledTexture, ledTextureGltf } from './ledTexture'
import { markSettled } from './ready'

/** 0 = rehearsal, 1 = showtime. Eased in Lights, read by stage materials. */
export const stageFx = { mix: 0 }
const lerp = (a: number, b: number, t: number) => a + (b - a) * t

type FxMats = { led: MeshStandardMaterial[]; strip: MeshStandardMaterial[]; cone: (MeshStandardMaterial | MeshBasicMaterial)[]; mark: MeshStandardMaterial[] }

function useFxMaterials(mats: FxMats) {
  useFrame(({ clock }) => {
    const k = stageFx.mix
    for (const m of mats.led) m.emissiveIntensity = lerp(0.2, 1.25, k)
    const pulse = 0.85 + 0.15 * Math.sin(clock.elapsedTime * 2.2)
    for (const m of mats.strip) m.emissiveIntensity = lerp(0.6, 3.2 * pulse, k)
    for (const m of mats.cone) m.opacity = 0.022 * k
    for (const m of mats.mark) m.emissiveIntensity = lerp(0.4, 2.0, k)
  })
}

function setupLed(m: MeshStandardMaterial, gltf = false) {
  const t = gltf ? ledTextureGltf() : ledTexture()
  m.map = t; m.emissiveMap = t; m.emissive = new Color('#ffffff'); m.color = new Color('#ffffff'); m.roughness = 0.6; m.metalness = 0; m.toneMapped = false; m.needsUpdate = true
}
function setupCone(m: MeshStandardMaterial | MeshBasicMaterial) {
  // FrontSide: a camera inside a cone sees nothing (no white-out on close shots)
  m.transparent = true; m.blending = AdditiveBlending; m.depthWrite = false; m.side = FrontSide; m.opacity = 0; m.toneMapped = false
  const sm = m as MeshStandardMaterial
  if (sm.isMeshStandardMaterial) {
    if (sm.emissive.getHex() === 0) sm.emissive.copy(sm.color.getHex() === 0 ? new Color('#fff1d6') : sm.color)
    sm.color.set('#000000'); sm.emissiveIntensity = 1; sm.roughness = 1; sm.metalness = 0
  }
  m.needsUpdate = true
}

const UP = new Vector3(0, 1, 0)
function Cone({ from, to, color, mat }: { from: Vector3; to: Vector3; color: string; mat: (m: MeshBasicMaterial) => void }) {
  const ref = useRef<Mesh>(null)
  const material = useMemo(() => { const m = new MeshBasicMaterial({ color }); setupCone(m); mat(m); return m }, [color, mat])
  const q = useMemo(() => new Quaternion(), [])
  const d = useMemo(() => new Vector3(), [])
  useFrame(() => {
    const o = ref.current
    if (!o) return
    d.subVectors(to, from)
    const len = d.length()
    o.position.copy(from).addScaledVector(d, 0.5)
    q.setFromUnitVectors(UP, d.multiplyScalar(-1 / len))
    o.quaternion.copy(q)
    o.scale.set(1, len, 1)
  })
  return <mesh ref={ref} material={material} renderOrder={3}><cylinderGeometry args={[0.04, 0.85, 1, 32, 1, true]} /></mesh>
}

export function PrimitiveStage() {
  const mats = useMemo<FxMats>(() => {
    const led = new MeshStandardMaterial(); setupLed(led)
    const strip = new MeshStandardMaterial({ color: '#0d1440', emissive: new Color('#3d7bff'), emissiveIntensity: 0.6, toneMapped: false })
    const mark = new MeshStandardMaterial({ color: '#111', emissive: new Color('#f2c14e'), emissiveIntensity: 0.4, toneMapped: false })
    return { led: [led], strip: [strip], cone: [], mark: [mark] }
  }, [])
  useFxMaterials(mats)
  const addCone = useMemo(() => (m: MeshBasicMaterial) => { if (!mats.cone.includes(m)) mats.cone.push(m) }, [mats])
  return (
    <group name="primitive_stage">
      <mesh position={[0, -0.46, 4]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <meshStandardMaterial color="#07070b" roughness={0.9} />
      </mesh>
      <mesh position={[0, -0.225, 0.6]} receiveShadow>
        <boxGeometry args={[9, 0.45, 5.4]} />
        <meshStandardMaterial color="#15151c" roughness={0.38} metalness={0.2} />
      </mesh>
      <mesh position={[0, -0.08, 3.31]} material={mats.strip[0] as Material}><boxGeometry args={[9, 0.035, 0.02]} /></mesh>
      <mesh position={[0, 0.004, 0]} rotation={[-Math.PI / 2, 0, 0]} material={mats.mark[0] as Material}><ringGeometry args={[0.36, 0.4, 48]} /></mesh>
      <mesh position={[0, 2.45, -2.1]} material={mats.led[0] as Material}><planeGeometry args={[7.4, 7.4 * 9 / 16]} /></mesh>
      <mesh position={[0, 2.45, -2.16]}><boxGeometry args={[7.6, 7.4 * 9 / 16 + 0.2, 0.1]} /><meshStandardMaterial color="#050508" roughness={0.5} /></mesh>
      <Cone from={ANCHORS.spot_L} to={ANCHORS.spot_target_L} color="#6f8cff" mat={addCone} />
      <Cone from={ANCHORS.spot_R} to={ANCHORS.spot_target_R} color="#ff5fae" mat={addCone} />
      <Cone from={ANCHORS.spot_C} to={ANCHORS.spot_target_C} color="#fff1d6" mat={addCone} />
    </group>
  )
}

/** IMAG: side screens (material led_wall_side) show a live close-up of the avatar, rendered every other frame. */
function useImag(screens: Mesh[], mats: MeshStandardMaterial[]) {
  const gl = useThree(s => s.gl)
  const scene = useThree(s => s.scene)
  const rt = useMemo(() => {
    const r = new WebGLRenderTarget(640, 360)
    r.texture.repeat.set(1, -1); r.texture.offset.set(0, 1) // render targets are bottom-up; glTF UVs are top-down
    return r
  }, [])
  const cam = useMemo(() => new PerspectiveCamera(24, 16 / 9, 0.1, 60), [])
  const frame = useRef(0)
  useLayoutEffect(() => {
    for (const m of mats) { m.map = rt.texture; m.emissiveMap = rt.texture; m.emissive.set('#ffffff'); m.color.set('#000000'); m.emissiveIntensity = 1; m.toneMapped = false; m.needsUpdate = true }
  }, [mats, rt])
  useEffect(() => () => rt.dispose(), [rt])
  useFrame(() => {
    if (!screens.length || (frame.current++ & 1)) return
    const a = live.avatar
    cam.position.set(a.x + 0.3, a.y + 1.5, a.z + 2.6)
    cam.lookAt(a.x, a.y + 1.3, a.z)
    for (const s of screens) s.visible = false
    const prev = gl.getRenderTarget()
    gl.setRenderTarget(rt)
    gl.render(scene, cam)
    gl.setRenderTarget(prev)
    for (const s of screens) s.visible = true
  })
}

/** stage.glb: copies empties into ANCHORS, wires led_wall / led_wall_side / led_strip / center_mark / light_cone materials. */
export function GlbStage() {
  const gltf = useGLTF(meshes.files.stage, DRACO_PATH)
  useLayoutEffect(() => markSettled('stage'), [])
  const imag = useMemo(() => ({ screens: [] as Mesh[], mats: [] as MeshStandardMaterial[] }), [gltf])
  const mats = useMemo<FxMats>(() => {
    const out: FxMats = { led: [], strip: [], cone: [], mark: [] }
    gltf.scene.updateMatrixWorld(true)
    const seen = new Set<Material>()
    gltf.scene.traverse((o: Object3D) => {
      // cam_audience in stage.glb is the speaker's POV (behind the avatar); keep our front-of-house shot instead
      if (o.name in ANCHORS && !o.name.startsWith('cam_audience')) o.getWorldPosition(ANCHORS[o.name as AnchorName])
      const mesh = o as Mesh
      if (!mesh.isMesh) return
      mesh.receiveShadow = true
      const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
      for (const mm of list) {
        const m = mm as MeshStandardMaterial
        if ((m.name || '').startsWith('led_wall_side')) { if (!imag.screens.includes(mesh)) imag.screens.push(mesh); if (!imag.mats.includes(m)) imag.mats.push(m); continue }
        if (seen.has(m)) continue
        seen.add(m)
        const n = m.name || ''
        if (n.startsWith('led_wall')) { setupLed(m, true); out.led.push(m) }
        else if (n.startsWith('led_strip')) { m.toneMapped = false; if (m.emissive && m.emissive.getHex() === 0) m.emissive.set('#3d7bff'); out.strip.push(m) }
        else if (n.startsWith('center_mark')) { m.toneMapped = false; if (m.emissive && m.emissive.getHex() === 0) m.emissive.set('#f2c14e'); out.mark.push(m) }
        else if (n.startsWith('light_cone')) { setupCone(m); mesh.renderOrder = 3; mesh.castShadow = false; out.cone.push(m) }
      }
    })
    return out
  }, [gltf, imag])
  useFxMaterials(mats)
  useImag(imag.screens, imag.mats)
  // portfolio hero: nothing between the camera and him (audience heads, floor monitors)
  useLayoutEffect(() => {
    if (PARAMS.mode !== 'persona') return
    gltf.scene.traverse(o => { if (/^(audience|floor_monitor)/.test(o.name)) o.visible = false })
  }, [gltf])
  return <primitive object={gltf.scene} />
}

/** Rehearsal (bright neutral) <-> Showtime (dark house, coloured spots). */
export function Lights() {
  const hemi = useRef<HemisphereLight>(null)
  const amb = useRef<AmbientLight>(null)
  const key = useRef<DirectionalLight>(null)
  const fill = useRef<DirectionalLight>(null)
  const rim = useRef<DirectionalLight>(null)
  const sL = useRef<SpotLight>(null), sR = useRef<SpotLight>(null), sC = useRef<SpotLight>(null)
  const targets = useMemo(() => [new Object3D(), new Object3D(), new Object3D()], [])
  const keyTarget = useMemo(() => new Object3D(), [])
  const scene = useThree(s => s.scene)
  const bgRehearsal = useMemo(() => new Color('#14141d'), [])
  const bgShow = useMemo(() => new Color('#020206'), [])
  useLayoutEffect(() => {
    if (sL.current) sL.current.target = targets[0]
    if (sR.current) sR.current.target = targets[1]
    if (sC.current) sC.current.target = targets[2]
    if (key.current) key.current.target = keyTarget
  }, [targets, keyTarget])
  useFrame(({ clock }, dt) => {
    const want = PARAMS.mode === 'persona' || useStore.getState().mode === 'show' ? 1 : 0
    stageFx.mix += (want - stageFx.mix) * Math.min(1, dt * 1.6)
    const k = easeInOutCubic(clamp01(stageFx.mix))
    if (hemi.current) hemi.current.intensity = lerp(1.15, 0.06, k)
    if (amb.current) amb.current.intensity = lerp(0.35, 0.02, k)
    if (key.current) {
      // persona hero keeps a warm key on him so the clothes still read under the blue/violet wash
      key.current.intensity = lerp(2.3, PARAMS.mode === 'persona' ? 1.25 : 0.15, k)
      if (PARAMS.mode === 'persona') key.current.color.set('#ffd8b0')
    }
    if (fill.current) fill.current.intensity = lerp(1.0, 0, k)
    if (rim.current) rim.current.intensity = lerp(0.9, 2.2, k)
    const pulse = 1 + 0.08 * Math.sin(clock.elapsedTime * 1.7)
    if (sL.current) { sL.current.position.copy(ANCHORS.spot_L); sL.current.intensity = lerp(0, 30, k) * pulse }
    if (sR.current) { sR.current.position.copy(ANCHORS.spot_R); sR.current.intensity = lerp(0, 30, k) / pulse }
    if (sC.current) { sC.current.position.copy(ANCHORS.spot_C); sC.current.intensity = lerp(0, 36, k) }
    targets[0].position.copy(ANCHORS.spot_target_L)
    targets[1].position.copy(ANCHORS.spot_target_R)
    targets[2].position.copy(ANCHORS.spot_target_C)
    keyTarget.position.set(0, 1, 0.8)
    if (scene.background instanceof Color) scene.background.lerpColors(bgRehearsal, bgShow, k)
    if (scene.fog && 'color' in scene.fog) (scene.fog.color as Color).lerpColors(bgRehearsal, bgShow, k)
  })
  return (
    <>
      <color attach="background" args={['#14141d']} />
      <fog attach="fog" args={['#14141d', 14, 34]} />
      <hemisphereLight ref={hemi} args={['#f3f1ff', '#2a2730', 1.15]} />
      <ambientLight ref={amb} intensity={0.35} />
      <directionalLight ref={key} position={[2.6, 5, 6]} intensity={2.3} color="#fffaf2" />
      <directionalLight ref={fill} position={[-4, 2.5, 4]} intensity={1} color="#e8eeff" />
      <directionalLight ref={rim} position={[0, 4, -4]} intensity={0.9} color="#9fb6ff" />
      <spotLight ref={sL} color="#5a6dff" angle={0.32} penumbra={0.6} decay={1.2} distance={30} intensity={0} />
      <spotLight ref={sR} color="#8a5cff" angle={0.32} penumbra={0.6} decay={1.2} distance={30} intensity={0} />
      <spotLight ref={sC} color="#fff1d6" angle={0.26} penumbra={0.45} decay={1.2} distance={30} intensity={0} />
      {targets.map((t, i) => <primitive key={i} object={t} />)}
      <primitive object={keyTarget} />
    </>
  )
}

type Shot = 'cam_fit' | 'cam_wide' | 'cam_audience' | 'cam_close'
export const SHOT_TIMES: [number, Shot][] = [[0, 'cam_wide'], [2.6, 'cam_audience'], [5.2, 'cam_close']]
export const SHOW_DURATION = 7.8

/** Eased camera moves between the stage's camera empties. */
export function CameraRig() {
  const camera = useThree(s => s.camera)
  const size = useThree(s => s.size)
  const st = useMemo(() => ({ shot: '' as Shot | '', t0: 0, fromPos: new Vector3(), fromTgt: new Vector3(), tgt: new Vector3().copy(ANCHORS.cam_fit_target), pos: new Vector3(), aim: new Vector3(), right: new Vector3() }), [])
  useFrame(({ clock }) => {
    if (PARAMS.mode === 'persona') {
      // portfolio hero: slow cinematic arc + slight dolly, head-to-toe framing, slightly low angle.
      // Works for a wide short frame (~16:6) and phones: distance fits 2.9 m of height and 1.5 m of width.
      const t = clock.elapsedTime
      const a = Math.sin(t * 0.085) * 0.5 + 0.12
      const aspect = size.width / Math.max(1, size.height)
      const pc = camera as PerspectiveCamera
      if (pc.fov !== 38) { pc.fov = 38; pc.updateProjectionMatrix() }
      const tan = Math.tan((pc.fov * Math.PI) / 360)
      const dist = Math.max(1.4 / tan, 0.8 / (tan * aspect)) * (1 + 0.05 * Math.sin(t * 0.13))
      const c = ANCHORS.mark_center
      st.aim.set(c.x, c.y + 1.0, c.z)
      camera.position.set(c.x + Math.sin(a) * dist, c.y + 0.9, c.z + Math.cos(a) * dist)
      camera.lookAt(st.aim)
      return
    }
    const { mode, showStart } = useStore.getState()
    let shot: Shot = 'cam_fit'
    if (mode === 'show') {
      const t = (performance.now() - showStart) / 1000
      for (const [at, s] of SHOT_TIMES) if (t >= at) shot = s
    }
    const now = clock.elapsedTime
    if (shot !== st.shot) {
      if (st.shot === '') { camera.position.copy(ANCHORS[shot]); st.tgt.copy(ANCHORS[(shot + '_target') as AnchorName]) }
      st.shot = shot; st.t0 = now; st.fromPos.copy(camera.position); st.fromTgt.copy(st.tgt)
    }
    const k = easeInOutCubic(clamp01((now - st.t0) / (REDUCED_MOTION ? 0.6 : 2.5)))
    st.pos.copy(ANCHORS[shot])
    st.aim.copy(ANCHORS[(shot + '_target') as AnchorName])
    const aspect = size.width / Math.max(1, size.height)
    if (shot === 'cam_fit') {
      // frame the whole avatar above the product rail: 3.5 m tall, 1.7 m wide window, centre at 0.42 m
      const tan = Math.tan(((camera as PerspectiveCamera).fov * Math.PI) / 360)
      const phone = aspect < 0.8 // phones: overlays top and bottom, so a taller window
      const bare = PARAMS.mode === 'locked' // no UI: frame the avatar alone
      const half = bare ? 1.2 : phone ? 2.4 : 1.75
      const dist = Math.max(half / tan, (bare ? 0.75 : 0.85) / (tan * aspect))
      st.aim.set(ANCHORS.avatar_fit.x, ANCHORS.avatar_fit.y + (bare ? 0.88 : phone ? 0.45 : 0.42), ANCHORS.avatar_fit.z)
      st.pos.sub(ANCHORS.cam_fit_target).normalize().multiplyScalar(dist).add(st.aim)
    } else {
      if (shot === 'cam_wide' && aspect >= 1.1 && aspect < 1.7) {
        // keep the IMAG side screens in the wide shot on narrower windows
        const f = Math.min(1.3, 1.7 / aspect); st.pos.sub(st.aim).multiplyScalar(f).add(st.aim)
      }
      if (shot === 'cam_close') {
        // keep the whole upper body in frame (judge the outfit, not the nose)
        const d = st.pos.distanceTo(st.aim)
        if (d < 3.6) st.pos.sub(st.aim).multiplyScalar(3.6 / d).add(st.aim)
        st.aim.y -= 0.2; st.pos.y -= 0.2
        if (aspect > 1.2) {
          // leave room on the right for the stage check card
          st.right.subVectors(st.aim, st.pos).normalize().cross(camera.up).multiplyScalar(0.45)
          st.aim.add(st.right); st.pos.add(st.right)
        }
      }
      if (aspect < 1.1) {
        // portrait screens: back the camera off so the whole avatar fits
        const f = Math.min(2.1, 1.1 / aspect); st.pos.sub(st.aim).multiplyScalar(f).add(st.aim)
      }
    }
    camera.position.lerpVectors(st.fromPos, st.pos, k)
    st.tgt.lerpVectors(st.fromTgt, st.aim, k)
    camera.lookAt(st.tgt)
  })
  return null
}
