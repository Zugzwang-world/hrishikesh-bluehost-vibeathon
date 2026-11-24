// Primitive avatar and garments on the same landmarks as avatar.glb (1.75 m, A-pose, faces +Z, feet at origin).
import { useMemo, type ReactNode } from 'react'
import { Quaternion, Vector3, type Material } from 'three'
import { RoundedBox } from '@react-three/drei'

type V3 = [number, number, number]
const UP = new Vector3(0, 1, 0)

export const L = {
  head: [0, 1.635, 0.005] as V3,
  shoulderL: [0.2, 1.42, 0] as V3, shoulderR: [-0.2, 1.42, 0] as V3,
  elbowL: [0.366, 1.18, -0.01] as V3, elbowR: [-0.366, 1.18, -0.01] as V3,
  wristL: [0.515, 0.967, 0.01] as V3, wristR: [-0.515, 0.967, 0.01] as V3,
  handL: [0.561, 0.9, 0.02] as V3, handR: [-0.561, 0.9, 0.02] as V3,
  hipL: [0.1, 0.93, 0] as V3, hipR: [-0.1, 0.93, 0] as V3,
  kneeL: [0.105, 0.52, 0.01] as V3, kneeR: [-0.105, 0.52, 0.01] as V3,
  ankleL: [0.11, 0.1, -0.01] as V3, ankleR: [-0.11, 0.1, -0.01] as V3,
}
const lerp3 = (a: V3, b: V3, t: number): V3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

/** Capsule from a to b. */
export function Seg({ a, b, r, material, name }: { a: V3; b: V3; r: number; material: Material; name?: string }) {
  const { pos, quat, len } = useMemo(() => {
    const va = new Vector3(...a), vb = new Vector3(...b)
    const dir = vb.clone().sub(va)
    const len = dir.length()
    return { pos: va.add(vb).multiplyScalar(0.5), quat: new Quaternion().setFromUnitVectors(UP, dir.normalize()), len }
  }, [a, b])
  return (
    <mesh name={name} position={pos} quaternion={quat} material={material} castShadow>
      <capsuleGeometry args={[r, Math.max(0.001, len), 6, 14]} />
    </mesh>
  )
}

export function PrimitiveBody({ skin, hair, hidden }: { skin: Material; hair: Material; hidden: Set<string> }) {
  const v = (n: string) => !hidden.has(n)
  return (
    <group name="primitive_body">
      {v('body_head') && <mesh name="body_head" position={L.head} material={skin} castShadow><sphereGeometry args={[0.105, 28, 20]} /></mesh>}
      {v('hair_full') && <mesh name="hair_full" position={[0, 1.66, -0.012]} scale={[1, 0.86, 1.05]} material={hair}><sphereGeometry args={[0.112, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.55]} /></mesh>}
      {v('hair_capped') && <mesh name="hair_capped" position={[0, 1.62, -0.02]} material={hair}><sphereGeometry args={[0.108, 20, 12, Math.PI * 0.15, Math.PI * 1.7, Math.PI * 0.35, Math.PI * 0.25]} /></mesh>}
      <mesh name="beard" position={[0, 1.585, 0.045]} scale={[1, 0.8, 0.8]} material={hair}><sphereGeometry args={[0.085, 20, 12, 0, Math.PI * 2, Math.PI * 0.45, Math.PI * 0.4]} /></mesh>
      {v('body_neck') && <Seg name="body_neck" a={[0, 1.45, 0]} b={[0, 1.56, 0.005]} r={0.05} material={skin} />}
      {v('body_torso') && <RoundedBox name="body_torso" args={[0.36, 0.5, 0.22]} radius={0.08} smoothness={4} position={[0, 1.215, 0]} material={skin} castShadow />}
      {v('body_hips') && <RoundedBox name="body_hips" args={[0.33, 0.16, 0.21]} radius={0.06} smoothness={3} position={[0, 0.97, 0]} material={skin} castShadow />}
      {v('body_upperarm_L') && <Seg name="body_upperarm_L" a={L.shoulderL} b={L.elbowL} r={0.048} material={skin} />}
      {v('body_upperarm_R') && <Seg name="body_upperarm_R" a={L.shoulderR} b={L.elbowR} r={0.048} material={skin} />}
      {v('body_forearm_L') && <Seg name="body_forearm_L" a={L.elbowL} b={L.wristL} r={0.04} material={skin} />}
      {v('body_forearm_R') && <Seg name="body_forearm_R" a={L.elbowR} b={L.wristR} r={0.04} material={skin} />}
      {v('body_hand_L') && <Seg name="body_hand_L" a={L.wristL} b={L.handL} r={0.032} material={skin} />}
      {v('body_hand_R') && <Seg name="body_hand_R" a={L.wristR} b={L.handR} r={0.032} material={skin} />}
      {v('body_thigh_L') && <Seg name="body_thigh_L" a={L.hipL} b={L.kneeL} r={0.07} material={skin} />}
      {v('body_thigh_R') && <Seg name="body_thigh_R" a={L.hipR} b={L.kneeR} r={0.07} material={skin} />}
      {v('body_shin_L') && <Seg name="body_shin_L" a={L.kneeL} b={L.ankleL} r={0.052} material={skin} />}
      {v('body_shin_R') && <Seg name="body_shin_R" a={L.kneeR} b={L.ankleR} r={0.052} material={skin} />}
      {v('body_foot_L') && <RoundedBox name="body_foot_L" args={[0.09, 0.07, 0.24]} radius={0.03} position={[0.11, 0.04, 0.045]} material={skin} />}
      {v('body_foot_R') && <RoundedBox name="body_foot_R" args={[0.09, 0.07, 0.24]} radius={0.03} position={[-0.11, 0.04, 0.045]} material={skin} />}
    </group>
  )
}

function Sleeves({ m, r, to }: { m: Material; r: number; to: 'elbow' | 'wrist' }) {
  return (
    <>
      <Seg a={lerp3(L.shoulderL, [0, 1.42, 0], 0.12)} b={L.elbowL} r={r} material={m} />
      <Seg a={lerp3(L.shoulderR, [0, 1.42, 0], 0.12)} b={L.elbowR} r={r} material={m} />
      {to === 'wrist' && <Seg a={L.elbowL} b={lerp3(L.elbowL, L.wristL, 0.94)} r={r * 0.86} material={m} />}
      {to === 'wrist' && <Seg a={L.elbowR} b={lerp3(L.elbowR, L.wristR, 0.94)} r={r * 0.86} material={m} />}
    </>
  )
}

function Jacket({ m, gap, len }: { m: Material; gap: number; len: number }) {
  const w = (0.43 - gap) / 2
  const cy = 1.47 - len / 2
  return (
    <>
      <RoundedBox args={[0.44, len, 0.17]} radius={0.06} smoothness={3} position={[0, cy, -0.045]} material={m} castShadow />
      <RoundedBox args={[w, len, 0.06]} radius={0.025} position={[gap / 2 + w / 2, cy, 0.1]} rotation={[0, -0.12, 0]} material={m} castShadow />
      <RoundedBox args={[w, len, 0.06]} radius={0.025} position={[-gap / 2 - w / 2, cy, 0.1]} rotation={[0, 0.12, 0]} material={m} castShadow />
      <Sleeves m={m} r={0.064} to="wrist" />
    </>
  )
}

export function PrimitiveGarment({ mesh, m, print }: { mesh: string; m: Material; print?: ReactNode }) {
  switch (mesh) {
    case 'top_tee':
      return <><RoundedBox args={[0.385, 0.53, 0.245]} radius={0.085} smoothness={4} position={[0, 1.205, 0]} material={m} castShadow /><Sleeves m={m} r={0.06} to="elbow" />{print}</>
    case 'top_oversized':
      return <><RoundedBox args={[0.44, 0.58, 0.27]} radius={0.1} smoothness={4} position={[0, 1.18, 0]} material={m} castShadow /><Sleeves m={m} r={0.072} to="elbow" />{print}</>
    case 'top_shirt':
      return <><RoundedBox args={[0.38, 0.54, 0.24]} radius={0.08} smoothness={4} position={[0, 1.2, 0]} material={m} castShadow /><Sleeves m={m} r={0.056} to="wrist" />
        <mesh position={[0, 1.47, 0.01]} rotation={[Math.PI / 2, 0, 0]} material={m}><torusGeometry args={[0.062, 0.016, 8, 24]} /></mesh>{print}</>
    case 'outer_blazer':
      return <Jacket m={m} gap={0.09} len={0.62} />
    case 'outer_overshirt':
      return <Jacket m={m} gap={0.05} len={0.6} />
    case 'bottom_slim':
    case 'bottom_wide': {
      const w = mesh === 'bottom_wide'
      return (
        <>
          <RoundedBox args={[0.355, 0.2, 0.235]} radius={0.07} smoothness={3} position={[0, 0.96, 0]} material={m} castShadow />
          <Seg a={L.hipL} b={L.kneeL} r={w ? 0.092 : 0.078} material={m} />
          <Seg a={L.hipR} b={L.kneeR} r={w ? 0.092 : 0.078} material={m} />
          {w ? <>
            <mesh position={lerp3(L.kneeL, L.ankleL, 0.5)} material={m} castShadow><cylinderGeometry args={[0.088, 0.105, 0.44, 18]} /></mesh>
            <mesh position={lerp3(L.kneeR, L.ankleR, 0.5)} material={m} castShadow><cylinderGeometry args={[0.088, 0.105, 0.44, 18]} /></mesh>
          </> : <>
            <Seg a={L.kneeL} b={L.ankleL} r={0.062} material={m} />
            <Seg a={L.kneeR} b={L.ankleR} r={0.062} material={m} />
          </>}
        </>
      )
    }
    case 'shoe_sneaker':
    case 'shoe_loafer': {
      const h = mesh === 'shoe_sneaker' ? 0.095 : 0.075
      return (
        <>
          <RoundedBox args={[0.11, h, 0.28]} radius={0.04} smoothness={3} position={[0.11, h / 2, 0.05]} material={m} castShadow />
          <RoundedBox args={[0.11, h, 0.28]} radius={0.04} smoothness={3} position={[-0.11, h / 2, 0.05]} material={m} castShadow />
        </>
      )
    }
    case 'head_cap':
      return <><mesh position={[0, 1.665, 0]} material={m} castShadow><sphereGeometry args={[0.118, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
        <mesh position={[0, 1.668, 0.12]} scale={[1, 1, 0.75]} material={m}><cylinderGeometry args={[0.1, 0.1, 0.012, 24, 1, false, -Math.PI / 2, Math.PI]} /></mesh></>
    case 'head_beanie':
      return <><mesh position={[0, 1.655, 0]} scale={[1, 1.18, 1]} material={m} castShadow><sphereGeometry args={[0.12, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
        <mesh position={[0, 1.665, 0]} rotation={[Math.PI / 2, 0, 0]} material={m}><torusGeometry args={[0.118, 0.02, 8, 28]} /></mesh></>
    case 'head_bucket':
      return <><mesh position={[0, 1.68, 0]} material={m} castShadow><cylinderGeometry args={[0.1, 0.122, 0.1, 24]} /></mesh>
        <mesh position={[0, 1.635, 0]} material={m}><cylinderGeometry args={[0.122, 0.18, 0.03, 28, 1, true]} /></mesh></>
    case 'eye_round':
      return <group position={[0, 1.645, 0.1]}>
        <mesh position={[0.042, 0, 0]} material={m}><torusGeometry args={[0.024, 0.0045, 8, 24]} /></mesh>
        <mesh position={[-0.042, 0, 0]} material={m}><torusGeometry args={[0.024, 0.0045, 8, 24]} /></mesh>
        <mesh material={m} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.003, 0.003, 0.036, 6]} /></mesh></group>
    case 'eye_shades':
      return <group position={[0, 1.645, 0.102]}>
        <RoundedBox args={[0.055, 0.032, 0.008]} radius={0.004} position={[0.034, 0, 0]} material={m} />
        <RoundedBox args={[0.055, 0.032, 0.008]} radius={0.004} position={[-0.034, 0, 0]} material={m} /></group>
    case 'watch_analog':
    case 'watch_digital':
      return <group position={lerp3(L.elbowL, L.wristL, 0.9)} rotation={[0, 0, Math.atan2(L.wristL[0] - L.elbowL[0], -(L.wristL[1] - L.elbowL[1]))]}>
        <mesh rotation={[0, 0, 0]} material={m}><cylinderGeometry args={[0.045, 0.045, 0.03, 20, 1, true]} /></mesh>
        {mesh === 'watch_analog'
          ? <mesh position={[0, 0, 0.045]} rotation={[Math.PI / 2, 0, 0]} material={m}><cylinderGeometry args={[0.02, 0.02, 0.01, 20]} /></mesh>
          : <RoundedBox args={[0.032, 0.03, 0.012]} radius={0.003} position={[0, 0, 0.045]} material={m} />}
      </group>
    case 'neck_chain':
      return <mesh position={[0, 1.455, 0.035]} rotation={[Math.PI / 2 - 0.35, 0, 0]} material={m}><torusGeometry args={[0.075, 0.006, 8, 40]} /></mesh>
    default:
      return null
  }
}
