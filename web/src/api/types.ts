// Shared types (Coordinator-owned). Lane D1 (scene/UI) and Lane D2 (stylist/stage check) both import these.
import type { Slot } from '../config'

export type Merchant = {
  slug: string; name: string; code: string; tagline: string; category: string; story: string
  brandColor: string; accentColor: string; logo: string; banner: string
}
export type Pattern = 'solid' | 'stripe' | 'check' | 'denim' | 'melange' | 'corduroy' | 'print'
export type Material = {
  color: string; pattern: Pattern; patternColor: string; printText: string | null; roughness: number; metalness: number
}
export type Product = {
  sku: string; merchant: string; name: string; slot: Slot; mesh: string; price: number; colorName: string
  description: string; tags: string[]; material: Material; image: string
}
export type Catalog = { version: number; currency: 'INR'; merchants: Merchant[]; products: Product[] }

/** slot -> SKU (null or missing = empty slot) */
export type Look = Partial<Record<Slot, string | null>>

export type StylistInput = { prompt: string; event: string; currentLook: Look }
export type StylistResult = {
  title: string
  look: Record<Slot, string | null>
  notes: { sku: string; why: string }[]
  stageNotes: string
  source: 'ai' | 'keywords'
}

/** Simple numbers computed in code before asking the model. All 0..1 unless noted. */
export type StageMetrics = {
  ledWallColor: string
  topContrast: number          // contrast of top (or outerwear if worn) vs LED wall colour, WCAG ratio (1..21)
  outerwearContrast: number | null
  brightnessUnderSpots: number // mean relative luminance of visible garments under the spot colour
  printReadability: number | null // contrast of printText vs its garment, WCAG ratio, null if no print
  merchants: number
  total: number                // rupees
}
export type StageCheckResult = {
  score: number                // 0..100
  verdict: string
  notes: string[]              // exactly three
  swap: { slot: Slot; sku: string; why: string } | null
  source: 'ai' | 'rules'
}
