import { useFrame, useThree } from '@react-three/fiber'
import { useRef, useMemo, useEffect, useCallback } from 'react'
import * as THREE from 'three'

export function CameraRig({
  children,
  enabled = true,
  intensity = 0.02,
  enableParallax = true,
}) {
  const { camera } = useThree()
  const targetRef = useRef(new THREE.Vector3())
  const targetGroupRef = useRef()
  const currentRef = useRef(new THREE.Vector2(0, 0))
  const targetPosRef = useRef(new THREE.Vector2(0, 0))
  const reducedMotion = useMemo(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    []
  )

  useFrame((state, delta) => {
    if (!enabled || reducedMotion) return

    if (enableParallax) {
      const x = (currentRef.current.x - state.size.width / 2) / (state.size.width / 2)
      const y = (currentRef.current.y - state.size.height / 2) / (state.size.height / 2)

      targetPosRef.current.x = THREE.MathUtils.lerp(targetPosRef.current.x, x * intensity, delta * 2)
      targetPosRef.current.y = THREE.MathUtils.lerp(targetPosRef.current.y, -y * intensity, delta * 2)

      camera.position.set(targetPosRef.current.x, targetPosRef.current.y, 6)
      
      if (targetGroupRef.current) {
        targetGroupRef.current.getWorldPosition(targetRef.current)
      }
      camera.lookAt(targetRef.current)
    }
  })

  const handleMouseMove = useCallback(
    (event) => {
      if (!enabled || reducedMotion) return
      currentRef.current.set(event.clientX, event.clientY)
    },
    [enabled, reducedMotion]
  )

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('mousemove', handleMouseMove)
      return () => window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [handleMouseMove])

  return (
    <group ref={targetGroupRef}>
      {children}
    </group>
  )
}

export function ScrollCamera({
  children,
  scrollY = 0,
  enabled = true,
}) {
  const { camera } = useThree()
  const reducedMotion = useMemo(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    []
  )

  useFrame(() => {
    if (!enabled || reducedMotion) return

    const scrollProgress = scrollY / (typeof window !== 'undefined' ? window.innerHeight : 1)
    const scrollFactor = Math.min(Math.max(scrollProgress, 0), 1)

    camera.position.set(
      0,
      THREE.MathUtils.lerp(0, 0.5, scrollFactor),
      THREE.MathUtils.lerp(6, 5.5, scrollFactor)
    )
    camera.lookAt(0, THREE.MathUtils.lerp(0, 0.3, scrollFactor), 0)
  })

  return <>{children}</>
}

export default CameraRig
