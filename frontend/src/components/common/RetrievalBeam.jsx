import { useFrame, useThree } from '@react-three/fiber'
import { Line, Text } from '@react-three/drei'
import { useRef, useMemo, useEffect, useState } from 'react'
import * as THREE from 'three'

const RETRIEVAL_STAGES = [
  { name: 'Document', color: 0xff6b6b, index: 0 },
  { name: 'Chunk', color: 0xffd93d, index: 1 },
  { name: 'Embed', color: 0x8b8dff, index: 2 },
  { name: 'Vector DB', color: 0x4ecdc4, index: 3 },
  { name: 'Retrieve', color: 0x6bcb77, index: 4 },
  { name: 'Rerank', color: 0xff6b9d, index: 5 },
  { name: 'Synthesize', color: 0x4d96ff, index: 6 },
  { name: 'Answer', color: 0xa855f7, index: 7 },
  { name: 'Cite', color: 0xc7ceea, index: 8 },
]

export function RetrievalBeam({
  nodes = [],
  active = false,
  intensity = 1,
  speed = 1,
  className
}) {
  const beamRef = useRef()
  const particlesRef = useRef([])
  const glowRef = useRef()
  const timeRef = useRef(0)
  const cycleRef = useRef(0)
  const pulseRef = useRef(0)
  const [particlePositions, setParticlePositions] = useState(new Float32Array(30 * 3))
  const [activeStage, setActiveStage] = useState(0)

  const stageNodes = useMemo(() => {
    if (nodes.length >= RETRIEVAL_STAGES.length) return nodes
    
    const defaultNodes = [
      [-4, 2, -2],
      [-2.5, 1.5, -1],
      [-1, 0.5, 0],
      [0, 0, 0],
      [1, -0.5, 0],
      [2.5, -1, 1],
      [4, -1.5, 1.5],
      [5, -2, 2],
      [6, -2.5, 2.5],
    ]
    return defaultNodes
  }, [nodes])

  useEffect(() => {
    particlesRef.current = []
    for (let i = 0; i < 30; i++) {
      // Deterministic pseudo-random based on index for purity
      particlesRef.current.push({
        position: new THREE.Vector3(),
        progress: i / 30,
        life: 0,
        maxLife: 3 + ((i * 11.3) % 1) * 2,
        size: 0.03 + ((i * 13.7) % 1) * 0.02,
        color: new THREE.Color(),
      })
    }
  }, [])

  useFrame((state, delta) => {
    timeRef.current += delta
    pulseRef.current += delta * 3

    if (!active) {
      if (beamRef.current?.material) {
        beamRef.current.material.opacity = THREE.MathUtils.lerp(
          beamRef.current.material.opacity, 0, delta * 2
        )
      }
      return
    }

    cycleRef.current += delta * speed * 0.3

    // Update active stage state for FloatingStageLabel
    const cycle = cycleRef.current % 1
    const newActiveStage = Math.floor(cycle * (RETRIEVAL_STAGES.length - 1))
    setActiveStage(newActiveStage)

    if (beamRef.current?.material) {
      beamRef.current.material.opacity = THREE.MathUtils.lerp(
        beamRef.current.material.opacity, 0.6 * intensity, delta * 2
      )
      beamRef.current.material.dashOffset = -timeRef.current * speed * 0.5
    }

    if (glowRef.current?.material) {
      glowRef.current.material.opacity = 0.2 * intensity * (0.5 + Math.sin(pulseRef.current) * 0.3)
      glowRef.current.scale.setScalar(1 + Math.sin(pulseRef.current) * 0.1)
    }

    particlesRef.current.forEach((particle) => {
      particle.life += delta
      if (particle.life > particle.maxLife) {
        particle.life = 0
        particle.progress = 0
      }

      const progress = particle.progress + delta * speed * 0.15
      particle.progress = progress

      const seg = Math.floor(progress * (RETRIEVAL_STAGES.length - 1))
      const segProgress = (progress * (RETRIEVAL_STAGES.length - 1)) % 1

      if (seg < RETRIEVAL_STAGES.length - 1 && stageNodes[seg] && stageNodes[seg + 1]) {
        const start = stageNodes[seg]
        const end = stageNodes[seg + 1]

        particle.position.set(
          start[0] + (end[0] - start[0]) * segProgress,
          start[1] + (end[1] - start[1]) * segProgress,
          start[2] + (end[2] - start[2]) * segProgress
        )

        const stageColor = RETRIEVAL_STAGES[seg].color
        const nextColor = RETRIEVAL_STAGES[seg + 1].color
        particle.color.lerpColors(
          new THREE.Color(stageColor),
          new THREE.Color(nextColor),
          segProgress
        )
      }
    })

    // Update all particle positions at once
    setParticlePositions(prev => {
      const newArray = new Float32Array(prev)
      particlesRef.current.forEach((particle, i) => {
        newArray[i * 3] = particle.position.x
        newArray[i * 3 + 1] = particle.position.y
        newArray[i * 3 + 2] = particle.position.z
      })
      return newArray
    })
  })

  const linePoints = useMemo(
    () => stageNodes.map((node) => new THREE.Vector3(...node)),
    [stageNodes]
  )

  const lineColors = useMemo(
    () => stageNodes.map((_, i) => new THREE.Color(RETRIEVAL_STAGES[Math.min(i, RETRIEVAL_STAGES.length - 1)].color)),
    [stageNodes]
  )

  const particleSizes = useMemo(() => {
    const sizes = new Float32Array(30)
    for (let i = 0; i < 30; i++) sizes[i] = 0.03 + ((i * 13.7) % 1) * 0.02
    return sizes
  }, [])

  // Use particlePositions and particleSizes directly in bufferAttribute

  if (!active) return null

  return (
    <group className={className}>
      <Line
        ref={beamRef}
        points={linePoints}
        vertexColors={lineColors}
        transparent
        opacity={0}
        lineWidth={8}
        dashed
        dashSize={0.3}
        gapSize={0.15}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />

      <group ref={glowRef}>
        {stageNodes.map((pos, i) => (
          <mesh key={i} position={pos}>
            <sphereGeometry args={[0.15, 16, 16]} />
            <meshBasicMaterial
              color={RETRIEVAL_STAGES[i].color}
              transparent
              opacity={0.4 * intensity}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        ))}
      </group>

      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={30} itemSize={3} array={particlePositions} usage={THREE.DynamicDrawUsage} />
          <bufferAttribute attach="attributes-size" count={30} itemSize={1} array={particleSizes} />
        </bufferGeometry>
        <pointsMaterial
          color={0x4ecdc4}
          transparent
          opacity={0.9}
          size={0.04}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {stageNodes.map((pos, i) => (
        <FloatingStageLabel
          key={i}
          position={pos}
          label={RETRIEVAL_STAGES[i].name}
          color={RETRIEVAL_STAGES[i].color}
          intensity={intensity}
          active={activeStage === i}
        />
      ))}
    </group>
  )
}

function FloatingStageLabel({ position, label, color, intensity, active }) {
  const { camera } = useThree()
  const labelRef = useRef()
  const textRef = useRef()
  const opacityRef = useRef(0)
  const scaleRef = useRef(0)

  useFrame((state, delta) => {
    if (!labelRef.current) return

    const targetOpacity = active ? 1 : 0.3
    opacityRef.current = THREE.MathUtils.lerp(opacityRef.current, targetOpacity * intensity, delta * 5)

    const targetScale = active ? 1.2 : 0.8
    scaleRef.current = THREE.MathUtils.lerp(scaleRef.current, targetScale, delta * 5)

    labelRef.current.lookAt(camera.position)
    labelRef.current.scale.setScalar(scaleRef.current)

    // Text from @react-three/drei returns a Group, access material via traverse
    if (textRef.current) {
      textRef.current.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.opacity = opacityRef.current
        }
      })
    }
  })

  return (
    <group ref={labelRef} position={[position[0], position[1] + 0.5, position[2]]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.5, 0.4]} />
        <meshBasicMaterial
          color={0x0a0a14}
          transparent
          opacity={0.8 * intensity}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0, 0.01]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.45, 0.35]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.9 * intensity}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      <Text
        ref={textRef}
        position={[0, 0, 0.02]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.12}
        color={0x0a0a14}
        anchorX="center"
        anchorY="middle"
        depthWrite={false}
      >
        {label}
      </Text>
    </group>
  )
}

export function RetrievalCycle({
  nodes,
  intensity = 1,
  className
}) {
  const timeRef = useRef(0)
  const activeStageRef = useRef(0)
  const stageProgressRef = useRef(0)

  useFrame((state, delta) => {
    timeRef.current += delta
    stageProgressRef.current += delta * 0.2

    if (stageProgressRef.current >= 1) {
      stageProgressRef.current = 0
      activeStageRef.current = (activeStageRef.current + 1) % (nodes.length - 1)
    }
  })

  return (
    <group className={className}>
      <RetrievalBeam
        nodes={nodes}
        active={true}
        intensity={intensity}
        speed={0.5}
      />
    </group>
  )
}

export default RetrievalBeam