// Guided bubbles for the Experience view. Dismissible (remembered in localStorage); tips=0 disables them.
// The layer never blocks clicks: only the bubbles themselves take pointer events.
import { useEffect, useState } from 'react'
import { useStore } from '../store'

const KEY = 'stage.tips.dismissed'
const disabledByUrl = new URLSearchParams(location.search).get('tips') === '0'
const wasDismissed = () => { try { return localStorage.getItem(KEY) === '1' } catch { return false } }

type Place = { top: number; left: number; side: 'up' | 'left' | 'down' } | null
type Tip = { n: number; text: string; sel: string; prefer: 'below' | 'right' | 'above' }
const TIPS: Tip[] = [
  { n: 1, text: 'Explain your vibe', sel: '.prompt-bar', prefer: 'below' },
  { n: 2, text: 'Pick pieces from any store', sel: '.store-card', prefer: 'right' },
  { n: 3, text: 'Lock the look', sel: '.btn--lock', prefer: 'above' },
]
const BW = 210, BH = 44

function place(t: Tip): Place {
  const el = document.querySelector(t.sel) as HTMLElement | null
  if (!el) return null
  const r = el.getBoundingClientRect()
  const W = window.innerWidth, H = window.innerHeight
  if (r.width === 0 || r.bottom < 0 || r.top > H) return null
  const clampX = (x: number) => Math.max(8, Math.min(W - BW - 8, x))
  if (t.prefer === 'right' && r.right + BW + 16 < W) return { top: Math.max(8, r.top + 34), left: r.right + 12, side: 'left' }
  if (t.prefer === 'above') return { top: Math.max(8, r.top - BH - 12), left: clampX(r.right - BW), side: 'down' }
  return { top: Math.min(H - BH - 8, r.bottom + 10), left: clampX(r.left + 20), side: 'up' }
}

export function Tips() {
  const mode = useStore(s => s.mode)
  const catalog = useStore(s => s.catalog)
  const [open, setOpen] = useState(() => !disabledByUrl && !wasDismissed())
  const [places, setPlaces] = useState<Place[]>([])

  useEffect(() => {
    if (!open || !catalog) return
    const update = () => setPlaces(TIPS.map(place))
    const t0 = window.setTimeout(update, 700) // after the cards spring in
    const iv = window.setInterval(update, 1000)
    window.addEventListener('resize', update)
    document.addEventListener('scroll', update, true)
    return () => { clearTimeout(t0); clearInterval(iv); window.removeEventListener('resize', update); document.removeEventListener('scroll', update, true) }
  }, [open, catalog])

  if (!open || mode !== 'fit' || !catalog) return null
  const dismiss = () => { setOpen(false); try { localStorage.setItem(KEY, '1') } catch { /* ignore */ } }
  return (
    <div className="tips" aria-label="Tips">
      {TIPS.map((t, i) => {
        const p = places[i]
        if (!p) return null
        return (
          <div key={t.n} className={'tip tip--' + p.side} style={{ top: p.top, left: p.left, ['--i' as string]: i }} role="note">
            <span className="tip__n">{t.n}</span>
            <span className="tip__text">{t.text}</span>
            {t.n === TIPS.length
              ? <button className="tip__ok" onClick={dismiss}>Got it</button>
              : <button className="tip__x" onClick={dismiss} aria-label="Close tips">×</button>}
          </div>
        )
      })}
    </div>
  )
}
