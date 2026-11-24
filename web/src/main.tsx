import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MotionConfig } from 'motion/react'
import './styles/tokens.css'
import App from './App'
// Fallback shop (Lane D3): /bag, /checkout, /orders, /store render ShopApp instead of the Stage.
// Bundled eagerly (about 8 kB gzip) so no lazy chunk can 404 after a redeploy.
import ShopApp from './shop/ShopApp'

const isShop = /^\/(bag|checkout|orders|store)(\/|$)/.test(location.pathname)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      {isShop ? <ShopApp /> : <App />}
    </MotionConfig>
  </StrictMode>,
)
