// Where "Add look to bag" goes when the URL has no host param. Set once the Bluehost app URL exists.
export const DEFAULT_HOST: string | null = null

export const SLOTS = ['top', 'outerwear', 'bottom', 'footwear', 'headwear', 'eyewear', 'watch', 'neckwear'] as const
export type Slot = (typeof SLOTS)[number]
export const REQUIRED: Slot[] = ['top', 'bottom', 'footwear']

// Persona default look (white tee, charcoal blazer, wide trousers, white sneakers).
export const DEFAULT_LOOK = ['KC-001', 'RS-001', 'IL-005', 'KB-001']
export const PERSONA = { name: 'Hrishikesh', event: 'On stage, Bluehost Bangalore' }
