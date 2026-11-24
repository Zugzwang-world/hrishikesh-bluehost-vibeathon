import { useEffect, useState } from 'react'

const memo = new Map<string, Promise<boolean>>()

/** True once the asset exists and is not the SPA html fallback. Never throws. */
export function assetExists(url: string): Promise<boolean> {
  let p = memo.get(url)
  if (!p) {
    p = fetch(url, { method: 'HEAD', cache: 'no-cache' })
      .then(r => r.ok && !(r.headers.get('content-type') || '').includes('text/html'))
      .catch(() => false)
    memo.set(url, p)
  }
  return p
}

export function useAssetExists(url: string): boolean {
  const [ok, setOk] = useState(false)
  useEffect(() => { let live = true; assetExists(url).then(v => { if (live) setOk(v) }); return () => { live = false } }, [url])
  return ok
}

export const DRACO_PATH = '/draco/'
