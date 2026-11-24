import type { AnchorHTMLAttributes, ReactNode } from 'react'
import { getBag, useLive } from './data'

export const NAV = 'suf-nav'
export function nav(to: string, replace = false) {
  if (replace) history.replaceState(null, '', to)
  else history.pushState(null, '', to)
  window.dispatchEvent(new Event(NAV))
}

export function Link({ to, children, ...rest }: { to: string; children: ReactNode } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a
      href={to}
      {...rest}
      onClick={e => {
        rest.onClick?.(e)
        if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0 || rest.target === '_blank') return
        e.preventDefault()
        nav(to)
      }}
    >
      {children}
    </a>
  )
}

export function TopBar() {
  useLive()
  const n = getBag().skus.length
  return (
    <header className="s-top">
      <a className="s-top__brand" href="/">SHOP-UNI-FY</a>
      <nav className="s-top__nav">
        <a href="/">Stage</a>
        <Link to="/bag">Bag{n ? <span className="s-top__count">{n}</span> : null}</Link>
        <Link to="/orders">My orders</Link>
      </nav>
    </header>
  )
}

export function StoreLogo({ slug, name, small }: { slug: string; name: string; small?: boolean }) {
  return <img className={small ? 's-logo s-logo--sm' : 's-logo'} src={`/merchants/${slug}.png`} alt={name} loading="lazy" />
}

export function Chip({ status, sample }: { status: string; sample?: boolean }) {
  return (
    <span className="s-chips">
      <span className={`s-chip s-chip--${status.toLowerCase()}`}>{status}</span>
      {sample ? <span className="s-chip s-chip--sample">Sample</span> : null}
    </span>
  )
}

