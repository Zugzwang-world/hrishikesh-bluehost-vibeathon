import { CART_PATH, DEFAULT_HOST } from '../config'

const p = new URLSearchParams(location.search)
const list = (v: string | null) => (v ? v.split(',').map(s => s.trim()).filter(Boolean) : null)
const path = location.pathname.replace(/\/+$/, '')

export type AppMode = 'experience' | 'persona' | 'locked' | 'product'
const m = p.get('mode')

export const PARAMS = {
  embed: p.get('embed') === '1',
  host: (p.get('host') || DEFAULT_HOST || '').replace(/\/+$/, ''),
  cartPath: '/' + (p.get('cartPath') || CART_PATH).replace(/^\/+/, ''),
  try: p.get('try')?.trim() || null,
  look: list(p.get('look')),
  event: p.get('event'),
  sku: p.get('sku')?.trim() || null,
  mode: (path === '/product' ? 'product' : m === 'persona' ? 'persona' : m === 'locked' ? 'locked' : 'experience') as AppMode,
}
