import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { MotionConfig } from 'motion/react'
import './styles/tokens.css'
import App from './App'

// Fallback shop (Lane D3): /bag, /checkout, /orders, /store render the lazily-loaded ShopApp instead of the Stage.
const ShopApp = lazy(() => import('./shop/ShopApp'))
const isShop = /^\/(bag|checkout|orders|store)(\/|$)/.test(location.pathname)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      {isShop ? <Suspense fallback={null}><ShopApp /></Suspense> : <App />}
    </MotionConfig>
  </StrictMode>,
)
