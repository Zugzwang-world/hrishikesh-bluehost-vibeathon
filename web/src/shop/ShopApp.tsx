// Fallback shop (Lane D3): /bag, /checkout, /orders, /store inside the Stage app. Lazy-loaded from main.tsx.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import './shop.css'
import { NAV, TopBar } from './nav'
import BagPage from './BagPage'
import CheckoutPage from './CheckoutPage'
import { OrderPage, OrdersList } from './OrdersPage'
import MerchantApp from './MerchantApp'

function useRoute() {
  const [loc, setLoc] = useState(() => ({ path: location.pathname, search: location.search }))
  useEffect(() => {
    const on = () => setLoc({ path: location.pathname, search: location.search })
    window.addEventListener('popstate', on)
    window.addEventListener(NAV, on)
    return () => { window.removeEventListener('popstate', on); window.removeEventListener(NAV, on) }
  }, [])
  return loc
}

export default function ShopApp() {
  const { path, search } = useRoute()
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => { root.current?.scrollTo({ top: 0 }) }, [path])
  const parts = path.replace(/\/+$/, '').split('/').filter(Boolean)
  const head = parts[0]
  const params = new URLSearchParams(search)
  let page: ReactNode
  let merchant = false
  if (head === 'checkout') page = <CheckoutPage />
  else if (head === 'orders') page = parts[1] ? <OrderPage number={decodeURIComponent(parts[1])} /> : <OrdersList />
  else if (head === 'store') { merchant = true; page = <MerchantApp slug={parts[1] ?? ''} order={params.get('order')} /> }
  else page = <BagPage add={params.get('add')} look={params.get('look')} />
  useEffect(() => { document.title = merchant ? 'Store admin · SHOP-UNI-FY' : 'SHOP-UNI-FY · Bag' }, [merchant])
  return (
    <div ref={root} className={merchant ? 'shop shop--admin' : 'shop'}>
      {merchant ? null : <TopBar />}
      {page}
    </div>
  )
}
