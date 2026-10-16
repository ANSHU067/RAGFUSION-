import { Canvas } from '@react-three/fiber'
import { useCallback, useRef, useState } from 'react'
import { ACESFilmicToneMapping, WebGLRenderer } from 'three'
import { HeroFallback } from './HeroFallback'

export function HeroCanvas({ children, antialias, pixelRatio, ...props }) {
  const [failed, setFailed] = useState(false)
  const rendererRef = useRef(null)

  // Initialize on the actual canvas before Fiber's asynchronous configure step.
  // A React boundary alone cannot catch a rejected renderer initialization.
  const attachCanvas = useCallback((canvas) => {
    if (!canvas) return
    let renderer
    let active = true
    const handleContextLost = (event) => {
      event.preventDefault()
      if (active) setFailed(true)
    }
    canvas.addEventListener('webglcontextlost', handleContextLost)
    try {
      const context = canvas.getContext('webgl2', { alpha: true, antialias })
      if (!context || context.isContextLost()) throw new Error('WebGL2 unavailable')
      renderer = new WebGLRenderer({
        canvas, context, alpha: true, antialias, logarithmicDepthBuffer: true,
      })
      renderer.toneMapping = ACESFilmicToneMapping
      renderer.toneMappingExposure = 1.1
      rendererRef.current = renderer
    } catch (error) {
      console.warn('Hero renderer unavailable; using static background.', error)
      setFailed(true)
    }
    return () => {
      active = false
      canvas.removeEventListener('webglcontextlost', handleContextLost)
      rendererRef.current = null
      renderer?.dispose()
    }
  }, [antialias])

  const getRenderer = useCallback(() => rendererRef.current, [])

  if (failed) return <HeroFallback />

  return (
    <Canvas
      {...props}
      ref={attachCanvas}
      gl={getRenderer}
      dpr={pixelRatio}
      fallback={<HeroFallback />}
    >
      {children}
    </Canvas>
  )
}
