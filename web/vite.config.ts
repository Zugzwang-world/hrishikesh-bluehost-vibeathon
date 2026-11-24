import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Ship three's Draco decoder at /draco/ (same origin, works offline and in production).
const DRACO_DIR = fileURLToPath(new URL('./node_modules/three/examples/jsm/libs/draco/gltf/', import.meta.url))
const DRACO_FILES = ['draco_decoder.js', 'draco_decoder.wasm', 'draco_wasm_wrapper.js']

function draco(): Plugin {
  return {
    name: 'stage-draco',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const f = req.url?.startsWith('/draco/') ? req.url.slice(7).split('?')[0] : ''
        if (!DRACO_FILES.includes(f)) return next()
        res.setHeader('Content-Type', f.endsWith('.wasm') ? 'application/wasm' : 'text/javascript')
        res.end(readFileSync(DRACO_DIR + f))
      })
    },
    generateBundle() {
      for (const f of DRACO_FILES) this.emitFile({ type: 'asset', fileName: 'draco/' + f, source: readFileSync(DRACO_DIR + f) })
    },
  }
}

export default defineConfig({
  plugins: [react(), draco()],
  build: { chunkSizeWarningLimit: 2500 },
})
