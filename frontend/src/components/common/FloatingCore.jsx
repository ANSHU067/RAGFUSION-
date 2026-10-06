import { useFrame } from '@react-three/fiber'
import { useRef, useMemo, useEffect } from 'react'
import * as THREE from 'three'

const InnerCore = ({ intensity }) => {
  const coreRef = useRef()
  const pulseRef = useRef(0)

  useFrame((state, delta) => {
    pulseRef.current += delta * 0.5
    const pulse = Math.sin(pulseRef.current) * 0.15 + 1
    
    if (coreRef.current) {
      coreRef.current.scale.setScalar(pulse * intensity)
      coreRef.current.rotation.y += delta * 0.05
      coreRef.current.rotation.x += delta * 0.02
    }
  })

  return (
    <group ref={coreRef}>
      <mesh>
        <sphereGeometry args={[0.8, 64, 64]} />
        <meshBasicMaterial color={0x8b8dff} transparent opacity={0.3 * intensity} side={THREE.DoubleSide} />
      </mesh>
      
      <mesh>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshBasicMaterial color={0x4ecdc4} transparent opacity={0.4 * intensity} side={THREE.DoubleSide} />
      </mesh>

      <mesh>
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshBasicMaterial color={0xff6b9d} transparent opacity={0.5 * intensity} side={THREE.DoubleSide} />
      </mesh>

      <mesh>
        <sphereGeometry args={[0.25, 32, 32]} />
        <meshBasicMaterial color={0xffffff} transparent opacity={0.8 * intensity} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

const RotatingRings = ({ intensity }) => {
  const ringRefs = useRef([])
  const groupRef = useRef()

  useFrame((state, delta) => {
    ringRefs.current.forEach((ring, i) => {
      if (ring) {
        ring.rotation.x += delta * (0.1 + i * 0.05) * intensity
        ring.rotation.y += delta * (0.08 + i * 0.03) * intensity
        ring.rotation.z += delta * (0.05 + i * 0.02) * intensity
      }
    })
  })

  const ringGeometries = useMemo(() => [
    new THREE.TorusGeometry(1.1, 0.02, 8, 64),
    new THREE.TorusGeometry(1.3, 0.015, 8, 64),
    new THREE.TorusGeometry(1.5, 0.01, 8, 64),
  ], [])

  const ringMaterials = useMemo(() => [
    new THREE.MeshBasicMaterial({ color: 0x8b8dff, transparent: true, opacity: 0.4 * intensity, side: THREE.DoubleSide }),
    new THREE.MeshBasicMaterial({ color: 0x4ecdc4, transparent: true, opacity: 0.3 * intensity, side: THREE.DoubleSide }),
    new THREE.MeshBasicMaterial({ color: 0xff6b9d, transparent: true, opacity: 0.25 * intensity, side: THREE.DoubleSide }),
  ], [intensity])

  return (
    <group ref={groupRef}>
      {ringGeometries.map((geo, i) => (
        <mesh key={i} ref={(el) => { ringRefs.current[i] = el }} geometry={geo} material={ringMaterials[i]} />
      ))}
    </group>
  )
}

const EmbeddingParticles = ({ intensity, count = 200 }) => {
  const pointsRef = useRef()
  const positionsRef = useRef()
  const velocitiesRef = useRef()
  const phasesRef = useRef()
  const timeRef = useRef(0)

  useEffect(() => {
    if (!pointsRef.current) return

    const positions = new Float32Array(count * 3)
    const velocities = new Float32Array(count * 3)
    const phases = new Float32Array(count)

    for (let i = 0; i < count; i++) {
      // Deterministic pseudo-random based on index for purity
      const radius = 0.5 + ((i * 41.3) % 1) * 0.7
      const theta = ((i * 43.7) % 1) * Math.PI * 2
      const phi = Math.acos(2 * ((i * 47.9) % 1) - 1)

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)

      velocities[i * 3] = (((i * 53.1) % 1) - 0.5) * 0.02
      velocities[i * 3 + 1] = (((i * 59.3) % 1) - 0.5) * 0.02
      velocities[i * 3 + 2] = (((i * 61.7) % 1) - 0.5) * 0.02

      phases[i] = ((i * 67.1) % 1) * Math.PI * 2
    }

    positionsRef.current = positions
    velocitiesRef.current = velocities
    phasesRef.current = phases

    pointsRef.current.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    pointsRef.current.geometry.attributes.position.needsUpdate = true
  }, [count])

  useFrame((state, delta) => {
    if (!pointsRef.current || !positionsRef.current) return
    
    timeRef.current += delta
    const positions = positionsRef.current
    const velocities = velocitiesRef.current
    const phases = phasesRef.current
    
    for (let i = 0; i < count; i++) {
      phases[i] += delta * 0.5
      
      positions[i * 3] += velocities[i * 3] + Math.sin(phases[i] + timeRef.current) * 0.001
      positions[i * 3 + 1] += velocities[i * 3 + 1] + Math.cos(phases[i] + timeRef.current) * 0.001
      positions[i * 3 + 2] += velocities[i * 3 + 2] + Math.sin(phases[i] * 0.7 + timeRef.current) * 0.001
      
      const dist = Math.sqrt(
        positions[i * 3] ** 2 + 
        positions[i * 3 + 1] ** 2 + 
        positions[i * 3 + 2] ** 2
      )
      
      if (dist > 1.2) {
        const factor = 1.1 / dist
        positions[i * 3] *= factor
        positions[i * 3 + 1] *= factor
        positions[i * 3 + 2] *= factor
      }
    }
    
    pointsRef.current.geometry.attributes.position.needsUpdate = true
    if (pointsRef.current.material) {
      pointsRef.current.material.opacity = 0.6 * intensity
      pointsRef.current.material.size = 0.02 * (1 + Math.sin(timeRef.current) * 0.2) * intensity
    }
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} itemSize={3} array={new Float32Array(count * 3)} />
      </bufferGeometry>
      <pointsMaterial color={0x8b8dff} transparent opacity={0.6} size={0.02} sizeAttenuation />
    </points>
  )
}

const OuterGlow = ({ intensity }) => {
  const mesh1Ref = useRef()
  const mesh2Ref = useRef()
  const pulseRef = useRef(1)

  useFrame((state) => {
    pulseRef.current = Math.sin(state.clock.getElapsedTime() * 0.5) * 0.1 + 1
    
    if (mesh1Ref.current) {
      mesh1Ref.current.scale.setScalar(pulseRef.current * intensity)
    }
    if (mesh2Ref.current) {
      mesh2Ref.current.scale.setScalar(pulseRef.current * intensity)
    }
  })

  return (
    <group>
      <mesh ref={mesh1Ref}>
        <sphereGeometry args={[1.8, 64, 64]} />
        <meshBasicMaterial color={0x8b8dff} transparent opacity={0.05 * intensity} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh ref={mesh2Ref}>
        <sphereGeometry args={[2.2, 64, 64]} />
        <meshBasicMaterial color={0x4ecdc4} transparent opacity={0.03 * intensity} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
    </group>
  )
}

export function FloatingCore({ intensity = 1, className }) {
  const groupRef = useRef()
  const timeRef = useRef(0)
  const floatRef = useRef(0)
  const scaleRef = useRef(1)

  useFrame((state, delta) => {
    timeRef.current += delta
    floatRef.current += delta * 0.3
    scaleRef.current = 1 + Math.sin(floatRef.current) * 0.02
    
    if (groupRef.current) {
      groupRef.current.scale.setScalar(scaleRef.current)
      groupRef.current.position.y = Math.sin(floatRef.current) * 0.1
      groupRef.current.rotation.y = timeRef.current * 0.02
    }
  })

  return (
    <group ref={groupRef} className={className}>
      <OuterGlow intensity={intensity} />
      
      <mesh>
        <sphereGeometry args={[1.5, 64, 64]} />
        <meshPhysicalMaterial
          color={0x8b8dff}
          transparent
          opacity={0.25 * intensity}
          transmission={0.85}
          roughness={0.08}
          metalness={0.1}
          ior={1.45}
          thickness={0.4}
          clearcoat={1}
          clearcoatRoughness={0.1}
          transmissionColor={new THREE.Color(0x8b8dff)}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      
      <RotatingRings intensity={intensity} />
      <InnerCore intensity={intensity} />
      <EmbeddingParticles intensity={intensity} />
    </group>
  )
}

export default FloatingCore