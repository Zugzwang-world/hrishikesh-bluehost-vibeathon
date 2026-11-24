import { DEFAULT_HOST } from '../config'

const p = new URLSearchParams(location.search)
const list = (v: string | null) => (v ? v.split(',').map(s => s.trim()).filter(Boolean) : null)

export const PARAMS = {
  embed: p.get('embed') === '1',
  host: (p.get('host') || DEFAULT_HOST || '').replace(/\/+$/, ''),
  try: p.get('try')?.trim() || null,
  look: list(p.get('look')),
  event: p.get('event'),
}
