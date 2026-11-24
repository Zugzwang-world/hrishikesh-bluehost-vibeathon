import { Component, useEffect, useState, type ReactNode } from 'react'
import { useProgress } from '@react-three/drei'
import { PERSONA } from './config'
import type { Catalog } from './api/types'
import { PARAMS } from './lib/params'
import { useStore } from './store'
import Scene, { hasWebGL } from './scene/Scene'
import { ShopRing } from './ui/ShopRing'
import { ProductRail } from './ui/ProductRail'
import { LookPanel } from './ui/LookPanel'
import { PromptBar } from './ui/PromptBar'
import { Controls, StageCheckCard } from './ui/Controls'
import './styles/app.css'

class SceneBoundary extends Component<{ fallback: ReactNode; children: ReactNode; onFail: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(e: unknown) { console.warn('[stage] 3D failed, showing hero', e); this.props.onFail() }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

function Loader({ ready }: { ready: boolean }) {
  const { active, progress } = useProgress()
  const [gone, setGone] = useState(false)
  const busy = !ready || (active && progress < 100)
  useEffect(() => {
    if (busy) return
    const t = window.setTimeout(() => setGone(true), 350)
    return () => clearTimeout(t)
  }, [busy])
  if (gone) return null
  const pct = ready ? Math.max(8, Math.round(progress || 100)) : 4
  return (
    <div className={'loader' + (busy ? '' : ' is-done')} role="status" aria-live="polite">
      <div className="loader__mark">STAGE</div>
      <div className="loader__bar"><span style={{ width: `${pct}%` }} /></div>
      <div className="loader__label">Setting the stage for {PERSONA.name}…</div>
    </div>
  )
}

function Hero() {
  return <div className="hero-fallback"><img src="/brand/hero.jpg" alt="" /></div>
}

export default function App() {
  const catalog = useStore(s => s.catalog)
  const mode = useStore(s => s.mode)
  const setCatalog = useStore(s => s.setCatalog)
  const [webgl, setWebgl] = useState(() => hasWebGL())
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let tries = 0
    const load = () => fetch('/catalog/catalog.json').then(r => r.json()).then((c: Catalog) => setCatalog(c)).catch(() => { if (++tries < 4) setTimeout(load, 800 * tries) })
    load()
  }, [setCatalog])

  const three = webgl && !failed
  return (
    <div className={'app' + (PARAMS.embed ? ' is-embed' : '')} data-mode={mode}>
      {!PARAMS.embed && (
        <header className="topbar">
          <div className="topbar__brand">STAGE <span className="dim">· {PERSONA.name}</span></div>
          <div className="topbar__event">{PERSONA.event}</div>
        </header>
      )}
      <main className="stage-area">
        {three ? <SceneBoundary fallback={<Hero />} onFail={() => { setFailed(true); setWebgl(false) }}><Scene /></SceneBoundary> : <Hero />}
        <div className="overlay">
          <PromptBar />
          {mode === 'fit' && <ShopRing />}
          <ProductRail />
          <Controls webgl={three} />
          <StageCheckCard />
          {mode === 'show' && <div className="show-title" aria-hidden><span>Showtime</span></div>}
        </div>
        {three && <Loader ready={!!catalog} />}
      </main>
      <LookPanel />
    </div>
  )
}
