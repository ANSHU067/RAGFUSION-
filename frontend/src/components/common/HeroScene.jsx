import { Canvas } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { Suspense, useMemo, useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import * as THREE from 'three'

import { Environment } from './Environment'
import { Lights } from './Lights'
import { CameraRig } from './CameraRig'
import { FloatingCore } from './FloatingCore'
import { OrbitingDocuments } from './OrbitingDocuments'
import { KnowledgeGraph } from './KnowledgeGraph'
import { EmbeddingParticles } from './OrbitingElements'
import { RetrievalBeam } from './RetrievalBeam'
import { GlassCards } from './GlassCards'
import { FloatingLabels } from './FloatingLabels'

const HeroSceneContent = ({
  inView = false,
  reducedMotion = false,
  quality = 'high',
  onQualityChange
}) => {
  const intensity = inView ? 1 : 0.35
  const [webglError, setWebglError] = useState(false)

  const retrievalNodes = useMemo(() => [
    [-4.5, 2, -1.5],
    [-3, 1.2, -0.8],
    [-1.5, 0.3, 0],
    [0, 0, 0],
    [1.5, -0.5, 0.5],
    [3, -1.2, 1],
    [4.5, -2, 1.5],
    [5.5, -2.5, 2],
  ], [])

  if (webglError) {
    return <FallbackHero />
  }

  const qualitySettings = {
    low: { antialias: false, pixelRatio: 1, orbitingDocs: 4, particles: 80, glassCards: 3, enablePostProcessing: false, enableGlow: false },
    medium: { antialias: true, pixelRatio: Math.min(window.devicePixelRatio, 1.5), orbitingDocs: 7, particles: 250, glassCards: 5, enablePostProcessing: true, enableGlow: true },
    high: { antialias: true, pixelRatio: Math.min(window.devicePixelRatio, 2), orbitingDocs: 10, particles: 400, glassCards: 6, enablePostProcessing: true, enableGlow: true },
  }

  const settings = qualitySettings[quality] || qualitySettings.high

  return (
    <Canvas
      gl={{
        preserveDrawingBuffer: true,
        antialias: settings.antialias,
        alpha: true,
        logarithmicDepthBuffer: true,
      }}
      camera={{
        position: [0, 0, 6],
        fov: 45,
        near: 0.1,
        far: 100,
      }}
      onCreated={({ gl }) => {
        gl.setPixelRatio(settings.pixelRatio)
        gl.toneMapping = THREE.ACESFilmicToneMapping
        gl.toneMappingExposure = 1.1
        gl.domElement.addEventListener('webglcontextlost', (event) => {
          event.preventDefault()
          setWebglError(true)
        })
      }}
    >
      <Suspense fallback={<LoadingFallback />}>
        <Environment />
        <Lights />
        <CameraRig enabled={!reducedMotion} intensity={0.015} enableParallax={!reducedMotion}>
          <FloatingCore intensity={intensity} quality={quality} />

          <OrbitingDocuments
            intensity={intensity * 0.9}
            count={settings.orbitingDocs}
          />

          <EmbeddingParticles
            count={settings.particles}
            radius={2.5}
            intensity={intensity * 0.7}
          />

          <KnowledgeGraph
            intensity={intensity * 0.8}
            nodeCount={8}
            showLabels={!reducedMotion}
            retrievalPaths={[
              [0, 1, 2, 3, 4, 5, 6, 7],
            ]}
          />

          <RetrievalBeam
            nodes={retrievalNodes}
            active={inView && !reducedMotion}
            intensity={intensity}
            speed={0.4}
          />

          <GlassCards
            count={settings.glassCards}
            radius={4.5}
            intensity={intensity * 0.8}
            quality={quality}
          />

          <FloatingLabels intensity={intensity} />
        </CameraRig>
      </Suspense>

      <Html fullscreen>
        <HeroOverlay inView={inView} quality={quality} onQualityChange={onQualityChange} />
      </Html>
    </Canvas>
  )
}

const LoadingFallback = () => (
  <Html center>
    <div className="flex flex-col items-center gap-4 text-muted-foreground">
      <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      <p className="text-sm">Initializing knowledge core...</p>
    </div>
  </Html>
)

const FallbackHero = () => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ duration: 0.6, delay: 0.2 }}
    className="absolute inset-0 flex items-center justify-center bg-gradient-radial from-primary/10 via-transparent to-transparent"
  >
    <div className="text-center p-8">
      <div className="w-48 h-48 mx-auto mb-8 rounded-full bg-linear-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center">
        <svg className="w-24 h-24 text-primary/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <h3 className="text-xl font-semibold">RAGFUSION AI Knowledge Core</h3>
      <p className="text-muted-foreground mt-2 max-w-sm mx-auto">
        Advanced multi-agent retrieval with citations, knowledge graphs, and hybrid search.
      </p>
    </div>
  </motion.div>
)

const HeroOverlay = ({ inView, quality, onQualityChange }) => {
  const scrollToNextSection = useCallback(() => {
    const nextSection = document.getElementById('product')
    if (nextSection) {
      nextSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else {
      // Fallback: scroll by viewport height
      window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })
    }
  }, [])

  return (
    <div className="absolute inset-0 pointer-events-none">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: inView ? 1 : 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        className="absolute inset-0 bg-linear-to-b from-primary/5 via-transparent to-primary/5 pointer-events-none"
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: inView ? 1 : 0, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 text-center pointer-events-auto"
        role="button"
        tabIndex={0}
        onClick={scrollToNextSection}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            scrollToNextSection()
          }
        }}
        style={{ cursor: 'pointer' }}
      >
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <kbd className="px-2 py-1 bg-muted rounded border">Scroll</kbd>
          <span>to explore</span>
        </div>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="mt-2 text-primary"
        >
          ▼
        </motion.div>
      </motion.div>

      <div className="absolute top-4 right-4 pointer-events-auto flex gap-2">
        <QualityToggle quality={quality} onQualityChange={onQualityChange} />
      </div>
    </div>
  )
}

const QualityToggle = ({ quality = 'high', onQualityChange }) => {
  const selectRef = useRef(null)

  // Re-attach event listener after quality change (Canvas remounts)
  useEffect(() => {
    const select = selectRef.current
    if (select) {
      select.value = quality
    }
  }, [quality])

  return (
    <select
      ref={selectRef}
      value={quality}
      onChange={(e) => onQualityChange?.(e.target.value)}
      className="bg-background/80 backdrop-blur-sm border border-border rounded-lg px-3 py-1.5 text-xs text-foreground"
      aria-label="Graphics quality"
    >
      <option value="high">High Quality</option>
      <option value="medium">Balanced</option>
      <option value="low">Performance</option>
    </select>
  )
}

export function HeroScene({
  inView = false,
  className = '',
  fallback = null
}) {
  const [reducedMotion] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
  const [quality, setQuality] = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem('hero-quality') || 'high' : 'high'
  )
  // Persist quality setting to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('hero-quality', quality)
    }
  }, [quality])

  // Force Canvas remount when quality changes to apply antialias setting
  const canvasKey = `hero-canvas-${quality}`

  return (
    <div className={`relative w-full h-full ${className}`}>
      <HeroSceneContent
        key={canvasKey}
        inView={inView}
        reducedMotion={reducedMotion}
        quality={quality}
        onQualityChange={setQuality}
      />
      {fallback}
    </div>
  )
}

export default HeroScene
