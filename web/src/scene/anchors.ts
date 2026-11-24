import { Vector3 } from 'three'

// Stage hooks from contract/meshes.json. Defaults match the primitive stage; stage.glb empties overwrite them in place.
export const ANCHORS = {
  cam_fit: new Vector3(0, 1.2, 6.9),
  cam_fit_target: new Vector3(0, 0.8, 1.6),
  cam_wide: new Vector3(0, 3.2, 10.5),
  cam_wide_target: new Vector3(0, 1.6, 0),
  cam_audience: new Vector3(-2.8, 1.15, 6.2),
  cam_audience_target: new Vector3(0, 1.45, 0),
  cam_close: new Vector3(0.7, 1.6, 2.0),
  cam_close_target: new Vector3(0, 1.45, 0),
  spot_L: new Vector3(-3.8, 5.2, 3.2),
  spot_R: new Vector3(3.8, 5.2, 3.2),
  spot_C: new Vector3(0, 6.2, 5.5),
  spot_target_L: new Vector3(-0.2, 0.9, 0),
  spot_target_R: new Vector3(0.2, 0.9, 0),
  spot_target_C: new Vector3(0, 1.2, 0),
  avatar_fit: new Vector3(0, 0, 1.6),
  mark_center: new Vector3(0, 0, 0),
}
export type AnchorName = keyof typeof ANCHORS

// Stage look constants (art direction may retune).
export const LED_WALL_COLOR = '#1b3fd6'
export const TALK_TITLE = 'Shipping with AI · Bluehost Bangalore'
export const SPEAKER = 'HRISHIKESH'

// Live avatar root position (written by Avatar each frame, read by the IMAG camera).
export const live = { avatar: new Vector3(0, 0, 1.6) }

// Shared mutable turntable state (no per-frame allocations, no React renders).
export const turntable = { yaw: 0, vel: 0, dragging: false, lastInteract: 0, faceAt: -1e9 }

export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
export const clamp01 = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t)
