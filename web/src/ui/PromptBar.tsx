import { useState, type FormEvent } from 'react'
import { askStylist } from '../lib/stylist'
import { KEYNOTE, OCCASION_LABEL, useStore } from '../store'

/** Free text + occasion chip. Calls the stylist and applies the look slot by slot. */
export function PromptBar() {
  const [text, setText] = useState('')
  const occasion = useStore(s => s.occasion)
  const thinking = useStore(s => s.thinking)
  const mode = useStore(s => s.mode)
  const set = useStore(s => s.set)

  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    const st = useStore.getState()
    if (!st.catalog || st.thinking) return
    const prompt = text.trim() || (st.occasion ? 'Sharp, confident keynote look that reads well on stage' : 'A sharp everyday look')
    set({ thinking: true })
    try {
      const r = await askStylist({ prompt, event: st.occasion ? OCCASION_LABEL : '', currentLook: st.look }, st.catalog)
      const notes: Record<string, string> = {}
      for (const n of r.notes ?? []) notes[n.sku] = n.why
      set({ notes, title: r.title || st.title, stageNotes: r.stageNotes || '' })
      useStore.getState().applyLook(r.look, 300)
    } catch (err) {
      console.warn('[stage] stylist failed', err)
    } finally {
      set({ thinking: false })
    }
  }

  if (mode !== 'fit') return null
  return (
    <form className={'prompt-bar' + (thinking ? ' is-thinking' : '')} onSubmit={submit}>
      <button type="button" className={'chip' + (occasion ? ' is-on' : '')} aria-pressed={!!occasion}
        onClick={() => set({ occasion: occasion ? null : KEYNOTE })}>
        {OCCASION_LABEL}
      </button>
      <input value={text} onChange={e => setText(e.target.value)} placeholder="Describe a look… “smart casual keynote, no tie”" aria-label="Describe a look" />
      <button className="btn btn--accent" type="submit" disabled={thinking}>{thinking ? 'Styling…' : 'Style me'}</button>
    </form>
  )
}
