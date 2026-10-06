import { useFrame } from '@react-three/fiber'
import { Line, Text } from '@react-three/drei'
import { useRef, useMemo, useEffect, useState } from 'react'
import * as THREE from 'three'

const NODE_COLORS = [0x8b8dff, 0x4ecdc4, 0xff6b9d, 0xffd93d, 0x6bcb77, 0x4d96ff]

export function EmbeddingParticles({
  count = 500,
  radius = 2,
  intensity = 1,
  colors = NODE_COLORS,
  className
}) {
  const pointsRef = useRef()
  const positionsRef = useRef()
  const velocitiesRef = useRef()
  const phasesRef = useRef()
  const colorRef = useRef()
  const sizeRef = useRef()
  const timeRef = useRef(0)

  useEffect(() => {
    if (!pointsRef.current) return

    const positions = new Float32Array(count * 3)
    const velocities = new Float32Array(count * 3)
    const phases = new Float32Array(count)
    const colors = new Float32Array(count * 3)
    const sizes = new Float32Array(count)

    for (let i = 0; i < count; i++) {
      // Deterministic pseudo-random based on index for purity
      const r = radius * (0.3 + ((i * 71.3) % 1) * 0.7)
      const theta = ((i * 73.9) % 1) * Math.PI * 2
      const phi = Math.acos(2 * ((i * 79.7) % 1) - 1)

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.6
      positions[i * 3 + 2] = r * Math.cos(phi)

      velocities[i * 3] = (((i * 83.1) % 1) - 0.5) * 0.005
      velocities[i * 3 + 1] = (((i * 89.3) % 1) - 0.5) * 0.005
      velocities[i * 3 + 2] = (((i * 97.7) % 1) - 0.5) * 0.005

      phases[i] = ((i * 101.3) % 1) * Math.PI * 2

      const color = new THREE.Color(colors[i % colors.length])
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b

      sizes[i] = 0.01 + ((i * 103.1) % 1) * 0.02
    }

    positionsRef.current = positions
    velocitiesRef.current = velocities
    phasesRef.current = phases
    colorRef.current = colors
    sizeRef.current = sizes

    pointsRef.current.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    pointsRef.current.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    pointsRef.current.geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
    pointsRef.current.geometry.attributes.position.needsUpdate = true
    pointsRef.current.geometry.attributes.color.needsUpdate = true
    pointsRef.current.geometry.attributes.size.needsUpdate = true
  }, [count, radius, colors])

  useFrame((state, delta) => {
    if (!pointsRef.current || !positionsRef.current) return

    timeRef.current += delta
    const positions = positionsRef.current
    const velocities = velocitiesRef.current
    const phases = phasesRef.current

    for (let i = 0; i < count; i++) {
      phases[i] += delta * 0.3

      const noiseX = Math.sin(phases[i] + timeRef.current * 0.5) * 0.002
      const noiseY = Math.cos(phases[i] + timeRef.current * 0.3) * 0.002
      const noiseZ = Math.sin(phases[i] * 0.7 + timeRef.current * 0.4) * 0.002

      positions[i * 3] += velocities[i * 3] + noiseX
      positions[i * 3 + 1] += velocities[i * 3 + 1] + noiseY
      positions[i * 3 + 2] += velocities[i * 3 + 2] + noiseZ

      const dist = Math.sqrt(
        positions[i * 3] ** 2 +
        positions[i * 3 + 1] ** 2 +
        positions[i * 3 + 2] ** 2
      )

      if (dist > radius * 1.2) {
        const factor = (radius * 1.1) / dist
        positions[i * 3] *= factor
        positions[i * 3 + 1] *= factor
        positions[i * 3 + 2] *= factor
      }
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true
    if (pointsRef.current.material) {
      pointsRef.current.material.opacity = 0.6 * intensity
      pointsRef.current.material.size = 0.015 * intensity
    }
  })

  return (
    <group className={className}>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={count} itemSize={3} array={new Float32Array(count * 3)} />
          <bufferAttribute attach="attributes-color" count={count} itemSize={3} array={new Float32Array(count * 3)} />
          <bufferAttribute attach="attributes-size" count={count} itemSize={1} array={new Float32Array(count)} />
        </bufferGeometry>
        <pointsMaterial
          vertexColors
          transparent
          opacity={0.6}
          size={0.015}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  )
}

export function RetrievalBeam({
  nodes,
  path = [0, 1, 2, 3, 4, 5, 6, 7],
  intensity = 1,
  active = false
}) {
  const beamRef = useRef()
  const particlesRef = useRef([])
  const particlePositionsRef = useRef(new Float32Array(20 * 3))
  const timeRef = useRef(0)
  const geometryRef = useRef()

  useFrame((state, delta) => {
    if (!active) return
    timeRef.current += delta

    particlesRef.current.forEach((p, i) => {
      p.life += delta
      if (p.life > p.maxLife) {
        p.life = 0
        p.index = 0
      }

      const pathProgress = p.life / p.maxLife
      const segmentIndex = Math.floor(pathProgress * (path.length - 1))
      const segmentProgress = (pathProgress * (path.length - 1)) % 1

      if (segmentIndex < path.length - 1 && nodes[path[segmentIndex]] && nodes[path[segmentIndex + 1]]) {
        const start = nodes[path[segmentIndex]]
        const end = nodes[path[segmentIndex + 1]]

        p.position.set(
          start[0] + (end[0] - start[0]) * segmentProgress,
          start[1] + (end[1] - start[1]) * segmentProgress,
          start[2] + (end[2] - start[2]) * segmentProgress
        )
      }

      // Update buffer attribute
      const posArray = particlePositionsRef.current
      posArray[i * 3] = p.position.x
      posArray[i * 3 + 1] = p.position.y
      posArray[i * 3 + 2] = p.position.z
    })

    if (beamRef.current?.material) {
      beamRef.current.material.opacity = 0.8 * intensity
    }
    if (geometryRef.current) {
      geometryRef.current.attributes.position.needsUpdate = true
    }
  })

  const linePoints = useMemo(() => {
    return path.map((idx) => nodes[idx]).filter(Boolean)
  }, [nodes, path])

  useEffect(() => {
    if (!particlesRef.current.length) {
      for (let i = 0; i < 20; i++) {
        particlesRef.current.push({
          position: new THREE.Vector3(),
          life: i * 0.1,
          maxLife: 2 + Math.random() * 2,
          index: 0,
        })
      }
    }
  }, [])

  if (!active) return null

  return (
    <group>
      <Line
        ref={beamRef}
        points={linePoints}
        color={0x4ecdc4}
        transparent
        opacity={0.5 * intensity}
        lineWidth={6}
        dashed
        dashSize={0.2}
        gapSize={0.1}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />

      <points ref={geometryRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={20} itemSize={3} array={new Float32Array(20 * 3)} usage={THREE.DynamicDrawUsage} />
          <bufferAttribute attach="attributes-size" count={20} itemSize={1} array={new Float32Array(20).fill(0.05)} />
        </bufferGeometry>
        <pointsMaterial
          color={0x4ecdc4}
          transparent
          opacity={1}
          size={0.05}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  )
}

export function FloatingDocuments({
  count = 8,
  radius = 3.5,
  intensity = 1,
  documents = [
    { type: 'pdf', label: 'Research.pdf', color: 0xff6b6b },
    { type: 'docx', label: 'Report.docx', color: 0x4ecdc4 },
    { type: 'txt', label: 'Notes.txt', color: 0xffd93d },
    { type: 'md', label: 'README.md', color: 0x8b8dff },
    { type: 'web', label: 'Article', color: 0xff6b9d },
    { type: 'csv', label: 'Data.csv', color: 0x6bcb77 },
    { type: 'img', label: 'Chart.png', color: 0x4d96ff },
    { type: 'api', label: 'API.json', color: 0xa855f7 },
  ],
  className
}) {
  const docsRef = useRef([])
  const timeRef = useRef(0)
  const [initialized, setInitialized] = useState(false)

  useFrame((state, delta) => {
    timeRef.current += delta

    docsRef.current.forEach((doc, i) => {
      if (!doc.group) return

      const orbitSpeed = 0.05 + (i % 3) * 0.02
      const orbitRadius = radius + Math.sin(timeRef.current * 0.3 + i) * 0.3

      doc.angle += delta * orbitSpeed
      doc.tilt += delta * 0.01

      doc.group.position.x = Math.cos(doc.angle) * orbitRadius
      doc.group.position.z = Math.sin(doc.angle) * orbitRadius
      doc.group.position.y = Math.sin(doc.angle * 0.7 + i) * 0.5 + Math.cos(timeRef.current + i) * 0.2

      doc.group.rotation.y += delta * 0.1
      doc.group.rotation.x = Math.sin(doc.tilt) * 0.1
      doc.group.rotation.z = Math.cos(doc.tilt) * 0.05
    })
  })

  useEffect(() => {
    if (!initialized) {
      for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2
        const tilt = ((i * 13.37) % 1) * Math.PI * 2

        docsRef.current[i] = {
          angle,
          tilt,
          group: null
        }
      }
      setInitialized(true)
    }
  }, [count, radius, intensity, documents, initialized])

  const docElements = useMemo(() => {
    const elements = []
    for (let i = 0; i < count; i++) {
      const doc = documents[i % documents.length]
      const angle = (i / count) * Math.PI * 2

      elements.push(
        <group
          key={i}
          ref={(el) => { if (el) docsRef.current[i].group = el }}
          position={[
            Math.cos(angle) * radius,
            Math.sin(angle * 0.7) * 0.5,
            Math.sin(angle) * radius
          ]}
        >
          <FloatingDocument
            type={doc.type}
            label={doc.label}
            color={doc.color}
            intensity={intensity}
            index={i}
          />
        </group>
      )
    }
    return elements
  }, [count, radius, intensity, documents])

  return <group className={className}>{docElements}</group>
}

function FloatingDocument({ type, label, color, intensity, index }) {
  const docRef = useRef()
  const [hovered, setHovered] = useState(false)
  const pulseRef = useRef(0)

  useFrame((state, delta) => {
    pulseRef.current += delta
    if (docRef.current) {
      docRef.current.position.y += Math.sin(pulseRef.current + index) * 0.001
      docRef.current.rotation.y += delta * 0.02
    }
  })

  const icons = {
    pdf: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0xff6b6b} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    docx: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0x4ecdc4} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    txt: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0xffd93d} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    md: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0x8b8dff} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    web: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0xff6b9d} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    csv: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0x6bcb77} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    img: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0x4d96ff} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
    api: (
      <mesh position={[0, 0, 0.05]} scale={0.8}>
        <planeGeometry args={[0.6, 0.8]} />
        <meshBasicMaterial color={0xa855f7} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
    ),
  }

  return (
    <group ref={docRef}>
      <mesh
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <boxGeometry args={[0.7, 0.9, 0.05]} />
        <meshPhysicalMaterial
          color={color}
          transparent
          opacity={hovered ? 0.3 : 0.15 * intensity}
          transmission={0.3}
          roughness={0.1}
          metalness={0}
          clearcoat={1}
          clearcoatRoughness={0.1}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0, 0.03]}>
        <planeGeometry args={[0.65, 0.85]} />
        <meshBasicMaterial color={0x0a0a14} transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>

      {icons[type] || icons.pdf}

      <mesh position={[0, -0.55, 0.05]} scale={0.5}>
        <planeGeometry args={[1.2, 0.3]} />
        <meshBasicMaterial
          color={0xffffff}
          transparent
          opacity={0.7 * intensity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      <Text position={[0, -0.55, 0.06]} fontSize={0.08} color={0x0a0a14} anchorX="center" anchorY="middle" depthWrite={false}>
        {label}
      </Text>

      <mesh scale={hovered ? 1.2 : 1}>
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.05 * intensity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}

export default EmbeddingParticles