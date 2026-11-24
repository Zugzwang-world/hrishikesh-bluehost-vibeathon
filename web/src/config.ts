// Where "Lock the look" goes when the URL has no host param. Set once the Bluehost app URL exists.
export const DEFAULT_HOST: string | null = null
// Cart path on the host (a cartPath URL param overrides it).
export const CART_PATH = '/cart'

export const SLOTS = ['top', 'outerwear', 'bottom', 'footwear', 'headwear', 'eyewear', 'watch', 'neckwear'] as const
export type Slot = (typeof SLOTS)[number]
export const REQUIRED: Slot[] = ['top', 'bottom', 'footwear']

// Persona default look: his outfit today (black poplin shirt, beige linen overshirt, light-wash baggy jeans,
// white court sneakers, his own thin gold hex frames, gold digital watch).
export const DEFAULT_LOOK = ['KT-002', 'KT-006', 'SW-001', 'KK-001', 'LL-006', 'SH-001']
// Hero look for the demo prompt.
export const STAGE_READY = { title: 'Stage Ready', skus: ['KT-001', 'KT-006', 'SW-001', 'KK-001', 'LL-001', 'LL-006', 'SH-001'] }
export const PERSONA = { name: 'Hrishikesh Hundekari', event: 'On stage · Small Business AI Builder Tour · Bengaluru' }
export const BRAND = 'SHOP-UNI-FY'
