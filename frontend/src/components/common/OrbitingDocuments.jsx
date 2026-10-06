import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { memo } from 'react'
import * as THREE from 'three'

const DOCUMENT_TYPES = [
  { type: 'pdf', color: 0xe74c3c },
  { type: 'docx', color: 0x2b579a },
  { type: 'txt', color: 0x7f8c8d },
  { type: 'md', color: 0x3498db },
  { type: 'web', color: 0x9b59b6 },
  { type: 'youtube', color: 0xff0000 },
  { type: 'csv', color: 0x27ae60 },
  { type: 'img', color: 0xe67e22 },
  { type: 'api', color: 0x1abc9c },
  { type: 'db', color: 0x34495e },
]

const DOCUMENT_GEOMETRY = [
  { width: 0.4, height: 0.55, depth: 0.05 },
  { width: 0.35, height: 0.5, depth: 0.04 },
  { width: 0.38, height: 0.52, depth: 0.03 },
]

function DocumentCard({
  docType,
  orbitRadius,
  orbitSpeed,
  initialAngle,
  tiltAxis,
  intensity = 1,
  index
}) {
  const timeRef = useRef(initialAngle)
  const floatRef = useRef(0)
  const initializedRef = useRef(false)
  const meshRef = useRef()
  const glowRef = useRef()

  useEffect(() => {
    if (!initializedRef.current) {
      // Deterministic pseudo-random based on index for purity
      floatRef.current = ((index * 13.37) % 1) * Math.PI * 2
      initializedRef.current = true
    }
  }, [index])

  const material = useMemo(() => ({
    color: docType.color,
    transparent: true,
    opacity: 0.9,
    transmission: 0.3,
    roughness: 0.1,
    metalness: 0.1,
    clearcoat: 0.5,
    clearcoatRoughness: 0.1,
    side: THREE.DoubleSide,
  }), [docType.color])

  const glowMaterial = useMemo(() => ({
    color: docType.color,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [docType.color])

  useFrame((state, delta) => {
    timeRef.current += delta * orbitSpeed * 0.5
    floatRef.current += delta * 0.5

    const angle = timeRef.current
    const x = Math.cos(angle) * orbitRadius
    const z = Math.sin(angle) * orbitRadius
    const y = Math.sin(floatRef.current) * 0.3 + Math.cos(angle * 0.7) * 0.2

    if (meshRef.current) {
      meshRef.current.position.set(x, y, z)
      meshRef.current.rotation.y = angle + Math.PI / 2
      meshRef.current.rotation.x = Math.sin(floatRef.current * 0.5) * 0.15 * tiltAxis[0]
      meshRef.current.rotation.z = Math.cos(floatRef.current * 0.3) * 0.1 * tiltAxis[2]
      meshRef.current.scale.setScalar(0.9 + Math.sin(floatRef.current * 0.7) * 0.05)
    }

    if (glowRef.current?.material) {
      glowRef.current.position.set(x, y, z)
      glowRef.current.scale.setScalar(1.3 + Math.sin(floatRef.current) * 0.1)
      glowRef.current.material.opacity = 0.15 * intensity * (0.8 + Math.sin(floatRef.current * 2) * 0.2)
    }
  })

  const geo = DOCUMENT_GEOMETRY[index % 3]

  return (
    <group ref={meshRef}>
      <mesh
        geometry={new THREE.BoxGeometry(geo.width, geo.height, geo.depth)}
        material={material}
        castShadow
        receiveShadow
      />
      
      <mesh ref={glowRef} scale={1.3}>
        <boxGeometry 
          args={[geo.width * 1.1, geo.height * 1.1, geo.depth * 2]} 
        />
        <meshBasicMaterial attach="material" {...glowMaterial} />
      </mesh>

      <mesh position={[0, 0, 0.04]}>
        <planeGeometry args={[0.3, 0.05]} />
        <meshBasicMaterial color={0xffffff} transparent opacity={0.3 * intensity} side={THREE.DoubleSide} />
      </mesh>

      <mesh position={[0, -0.15, 0.04]}>
        <planeGeometry args={[0.25, 0.04]} />
        <meshBasicMaterial color={0xffffff} transparent opacity={0.2 * intensity} side={THREE.DoubleSide} />
      </mesh>

      <mesh position={[0, 0.15, 0.04]}>
        <planeGeometry args={[0.2, 0.03]} />
        <meshBasicMaterial color={0xffffff} transparent opacity={0.15 * intensity} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

const DocumentCardMemo = memo(DocumentCard)

export function OrbitingDocuments({ intensity = 1, count = 10, className }) {
  const documents = useMemo(() => {
    const docs = []
    for (let i = 0; i < count; i++) {
      const docType = DOCUMENT_TYPES[i % DOCUMENT_TYPES.length]
      // Deterministic pseudo-random based on index for purity
      const radius = 3.5 + ((i * 7.3) % 1) * 2.5
      const speed = 0.05 + ((i * 11.7) % 1) * 0.15
      const angle = (i / count) * Math.PI * 2 + ((i * 13.1) % 1) * 0.5
      const tilt = [
        0.5 + ((i * 17.3) % 1) * 0.5,
        0,
        0.3 + ((i * 19.7) % 1) * 0.3
      ]
      docs.push({ docType, orbitRadius: radius, orbitSpeed: speed, initialAngle: angle, tiltAxis: tilt, index: i })
    }
    return docs
  }, [count])

  return (
    <group className={className}>
      {documents.map((doc, i) => (
        <DocumentCardMemo 
          key={i}
          {...doc}
          intensity={intensity}
        />
      ))}
      
      <AmbientParticles count={30} intensity={intensity} />
    </group>
  )
}

function AmbientParticles({ count, intensity }) {
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const radius = 3 + ((i * 23.7) % 1) * 4
      const theta = ((i * 29.3) % 1) * Math.PI * 2
      const phi = Math.acos(2 * ((i * 31.1) % 1) - 1)
      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = radius * Math.cos(phi)
    }
    return pos
  }, [count])

  const colors = useMemo(() => {
    const col = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const docType = DOCUMENT_TYPES[i % DOCUMENT_TYPES.length]
      const color = new THREE.Color(docType.color)
      col[i * 3] = color.r
      col[i * 3 + 1] = color.g
      col[i * 3 + 2] = color.b
    }
    return col
  }, [count])

  const sizes = useMemo(() => {
    const sz = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      sz[i] = 0.02 + ((i * 37.9) % 1) * 0.04
    }
    return sz
  }, [count])

  const timeRef = useRef(0)
  const positionsRef = useRef(positions)

  useFrame((state, delta) => {
    timeRef.current += delta
    const pos = positionsRef.current
    for (let i = 0; i < count; i++) {
      const t = timeRef.current * (0.1 + i * 0.005)
      pos[i * 3] += Math.sin(t) * 0.001
      pos[i * 3 + 1] += Math.cos(t * 0.7) * 0.001
      pos[i * 3 + 2] += Math.sin(t * 0.5) * 0.001
    }
    positionsRef.current = pos
  })

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={positions} itemSize={3} usage={THREE.DynamicDrawUsage} />
        <bufferAttribute attach="attributes-color" array={colors} itemSize={3} />
        <bufferAttribute attach="attributes-size" array={sizes} itemSize={1} />
      </bufferGeometry>
      <pointsMaterial
        vertexColors
        size={0.05}
        sizeAttenuation
        transparent
        opacity={0.6 * intensity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

export default OrbitingDocuments