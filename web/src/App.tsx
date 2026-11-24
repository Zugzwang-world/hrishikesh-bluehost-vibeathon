import { Component, Suspense, useEffect, useState, type ReactNode } from 'react'
import { useProgress } from '@react-three/drei'
import { BRAND, PERSONA } from './config'
import type { Catalog } from './api/types'
import { PARAMS } from './lib/params'
import { useStore } from './store'
import Scene, { hasWebGL } from './scene/Scene'
import ProductView from './scene/ProductView'
import { assetExists } from './scene/assets'
import { fireReady } from './scene/ready'
import meshes from './contract/meshes.json'
import { ProductRail } from './ui/ProductRail'
import { PromptBar } from './ui/PromptBar'
import { Controls, StageCheckCard } from './ui/Controls'
import { StoreCard } from './ui/StoreCard'
import { LookBar } from './ui/LookBar'
import './styles/app.css'


class SceneBoundary extends Component<{ fallback: ReactNode; children: ReactNode; onFail: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(e: unknown) { console.warn('[stage] 3D failed, showing hero', e); this.props.onFail() }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

function Loader({ ready, minimal }: { ready: boolean; minimal?: boolean }) {
  const { active, progress } = useProgress()
  const [gone, setGone] = useState(false)
  const busy = !ready || (active && progress < 100)
  useEffect(() => {
    if (busy) return
    const t = window.setTimeout(() => setGone(true), 600)
    return () => clearTimeout(t)
  }, [busy])
  if (gone) return null
  const pct = ready ? Math.max(8, Math.round(progress || 100)) : 4
  return (
    <div className={'loader' + (busy ? '' : ' is-done') + (minimal ? ' loader--minimal' : '')} role="status" aria-live="polite">
      <div className="loader__mark">{BRAND}</div>
      <div className="loader__bar"><span style={{ width: `${pct}%` }} /></div>
      {!minimal && <div className="loader__label">Setting the stage for {PERSONA.name}…</div>}
    </div>
  )
}

function ProductImage() {
  const catalog = useStore(s => s.catalog)
  const p = catalog?.products.find(x => x.sku === PARAMS.sku) ?? catalog?.products[0]
  return p ? <img className="product-fallback" src={p.image} alt={p.name} /> : null
}

/** "AI render of Hrishikesh" caption and the Restyling… pill while the nearest render stands in. */
function CutoutCaption({ tiny }: { tiny?: boolean }) {
  const caption = useStore(s => s.cutoutCaption)
  const exact = useStore(s => s.cutoutExact)
  const mode = useStore(s => s.mode)
  if (!caption) return null
  return (
    <>
      <div className={'cutout-caption' + (tiny ? ' cutout-caption--tiny' : '')}>{caption}</div>
      {!exact && !tiny && mode === 'fit' && <div className="restyling" role="status">Restyling…</div>}
    </>
  )
}

function Hero() {
  return <div className="hero-fallback"><img src="/brand/hero.jpg" alt="" /></div>
}

function useBoot() {
  const setCatalog = useStore(s => s.setCatalog)
  const [checked, setChecked] = useState(false)
  useEffect(() => {
    let tries = 0
    const load = () => fetch('/catalog/catalog.json', { cache: 'no-cache' }).then(r => r.json()).then((c: Catalog) => setCatalog(c)).catch(() => { if (++tries < 4) setTimeout(load, 800 * tries) })
    load()
    const f = meshes.files
    const t = window.setTimeout(() => setChecked(true), 4000)
    Promise.all([assetExists(f.avatar), assetExists(f.wardrobe), assetExists(f.stage)]).then(() => setChecked(true))
    return () => clearTimeout(t)
  }, [setCatalog])
  return checked
}

export default function App() {
  const catalog = useStore(s => s.catalog)
  const mode = useStore(s => s.mode)
  const checked = useBoot()
  const [webgl, setWebgl] = useState(() => hasWebGL())
  const [failed, setFailed] = useState(false)
  const three = webgl && !failed
  useEffect(() => { if (!three) fireReady() }, [three])
  const scene = three
    ? <SceneBoundary fallback={<Hero />} onFail={() => { setFailed(true); setWebgl(false) }}><Scene /></SceneBoundary>
    : <Hero />

  // product drawer: one piece on an invisible mannequin
  if (PARAMS.mode === 'product') {
    return (
      <div className="app app--bare app--product">
        {three ? <Suspense fallback={null}><SceneBoundary fallback={<ProductImage />} onFail={() => setFailed(true)}><ProductView /></SceneBoundary></Suspense> : <ProductImage />}
      </div>
    )
  }
  // persona (portfolio) and locked (cart page): avatar only, no UI
  if (PARAMS.mode === 'persona' || PARAMS.mode === 'locked') {
    return (
      <div className="app app--bare">
        <main className="stage-area">{scene}<CutoutCaption tiny /></main>
      </div>
    )
  }

  const ms = catalog?.merchants ?? []
  return (
    <div className={'app' + (PARAMS.embed ? ' is-embed' : '')} data-mode={mode}>
      {!PARAMS.embed && (
        <header className="topbar">
          <div className="topbar__brand">{BRAND} <span className="topbar__serif">the whole look, from Bengaluru's thrift stores</span></div>
          <div className="topbar__event">{PERSONA.event}</div>
        </header>
      )}
      <div className="exp">
        <div className="exp__prompt">
          <div className="chapter">
            <div className="chapter__tag">03 / 05 · The Experience</div>
            <div className="chapter__line">Style one look from five thrift stores on my avatar, then lock it.</div>
          </div>
          <PromptBar />
        </div>
        <aside className="exp__col exp__col--left">{ms.slice(0, 2).map((m, i) => <StoreCard key={m.slug} m={m} index={i} />)}</aside>
        <main className="stage-area">
          {scene}
          <div className="overlay">
            <ProductRail />
            <Controls webgl={three} />
            <StageCheckCard />
            {mode === 'show' && <div className="show-title" aria-hidden><span>Showtime</span></div>}
            <CutoutCaption />
          </div>
          {three && <Loader ready={!!catalog && checked} />}
        </main>
        <aside className="exp__col exp__col--right">{ms.slice(2, 4).map((m, i) => <StoreCard key={m.slug} m={m} index={i + 2} />)}</aside>
        <footer className="exp__foot">
          {ms.slice(4).map((m, i) => <StoreCard key={m.slug} m={m} index={i + 4} strip />)}
          <LookBar />
        </footer>
      </div>
    </div>
  )
}
