import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { computeStageMetrics, stageCheck } from '../lib/stylist'
import { inr } from '../lib/bag'
import { productBySku, useStore } from '../store'
import { STAGE_READY } from '../config'
import { LED_WALL_COLOR } from '../scene/anchors'
import { SHOW_DURATION } from '../scene/Stage'
import { snapshot } from '../scene/Scene'

async function runCheck() {
  const st = useStore.getState()
  if (!st.catalog) return
  const look = st.look
  const metrics = computeStageMetrics(look, st.catalog, LED_WALL_COLOR)
  const r = await stageCheck(look, metrics, st.catalog)
  if (useStore.getState().look === look) useStore.getState().set({ check: r })
}

export function Controls({ webgl }: { webgl: boolean }) {
  const mode = useStore(s => s.mode)
  const setMode = useStore(s => s.setMode)
  const surprise = useStore(s => s.surprise)
  const timer = useRef(0)

  const goOnStage = () => {
    setMode('show')
    useStore.getState().set({ sheetOpen: false })
    void runCheck()
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => useStore.getState().set({ checkVisible: true }), (webgl ? SHOW_DURATION : 0.4) * 1000)
  }
  const back = () => { clearTimeout(timer.current); setMode('fit') }
  useEffect(() => () => clearTimeout(timer.current), [])

  return (
    <div className="controls">
      {mode === 'fit' ? (
        <>
          <button className="btn btn--ghost" onClick={surprise}>Surprise me</button>
          <button className="btn btn--ghost" onClick={() => useStore.getState().preset(STAGE_READY.title, STAGE_READY.skus)}>{STAGE_READY.title}</button>
          {webgl && <button className="btn btn--ghost" onClick={() => snapshot('hrishikesh-look.png')}>Snapshot</button>}
          <button className="btn btn--primary btn--stage" onClick={goOnStage}>Go on stage</button>
        </>
      ) : (
        <>
          {webgl && <button className="btn btn--ghost" onClick={() => snapshot('hrishikesh-on-stage.png')}>Snapshot</button>}
          <button className="btn btn--ghost" onClick={back}>Back to fitting</button>
        </>
      )}
    </div>
  )
}

export function StageCheckCard() {
  const check = useStore(s => s.check)
  const visible = useStore(s => s.checkVisible)
  const mode = useStore(s => s.mode)
  const catalog = useStore(s => s.catalog)
  const look = useStore(s => s.look)
  const equip = useStore(s => s.equip)
  const show = mode === 'show' && visible
  const swapP = check?.swap ? productBySku(catalog, check.swap.sku) : undefined
  const swapOn = !!(check?.swap && look[check.swap.slot] === check.swap.sku)
  const r = 34, circ = 2 * Math.PI * r

  useEffect(() => { if (show && !check) void runCheck() }, [show, check])

  return (
    <AnimatePresence>
      {show && (
        <motion.div className="stage-check" initial={{ opacity: 0, y: 24, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 16 }}
          transition={{ type: "spring", stiffness: 260, damping: 24 }} role="dialog" aria-label="Stage check">
          {!check ? <div className="stage-check__loading">Checking the look under the lights…</div> : (
            <>
              <div className="stage-check__top">
                <svg className="score-ring" viewBox="0 0 80 80" aria-hidden>
                  <circle cx="40" cy="40" r={r} className="score-ring__track" />
                  <circle cx="40" cy="40" r={r} className="score-ring__fill" strokeDasharray={circ} strokeDashoffset={circ * (1 - check.score / 100)} />
                </svg>
                <div className="score-num">{check.score}</div>
                <div>
                  <div className="eyebrow">Stage check</div>
                  <div className="stage-check__verdict">{check.verdict}</div>
                </div>
              </div>
              <ol className="stage-check__notes">{check.notes.slice(0, 3).map((n, i) => <li key={i}>{n}</li>)}</ol>
              {check.swap && swapP && (
                <div className="stage-check__swap">
                  <img src={swapP.image} alt="" />
                  <div>
                    <div className="eyebrow">One swap</div>
                    <div className="look-item__name">{swapP.name} <span className="dim">· {inr(swapP.price)}</span></div>
                    <div className="look-item__note">{check.swap.why}</div>
                  </div>
                  <button className="btn btn--accent" disabled={swapOn} onClick={() => { equip(check.swap!.sku); window.setTimeout(() => void runCheck(), 50) }}>{swapOn ? 'Applied' : 'Apply'}</button>
                </div>
              )}
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
