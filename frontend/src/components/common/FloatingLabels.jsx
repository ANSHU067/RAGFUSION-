import { useRef, useMemo, useEffect, memo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import * as THREE from 'three'

const FLOATING_LABELS = [
  { label: 'AI Knowledge Core', position: [0, 2.5, 0], color: 0x8b8dff, size: 1.2 },
  { label: 'Vector Embeddings', position: [-3, -1, 2], color: 0x4ecdc4, size: 0.9 },
  { label: 'Hybrid Retrieval', position: [3, 1, -2], color: 0xff6b9d, size: 0.9 },
  { label: 'Citation Engine', position: [-2, 2, 3], color: 0xffd93d, size: 0.8 },
  { label: 'Multi-Agent AI', position: [2, -2, -3], color: 0x6bcb77, size: 0.8 },
  { label: 'Knowledge Graph', position: [3, -1, 2], color: 0x4d96ff, size: 0.8 },
  { label: 'Secure Workspace', position: [-3, 1, -2], color: 0xa855f7, size: 0.8 },
]

function FloatingLabelMesh({ label, position, color, size = 1, intensity = 1, alwaysVisible = false }) {
  const { camera } = useThree()
  const labelRef = useRef()
  const textRef = useRef()
  const opacityRef = useRef(0)
  const scaleRef = useRef(0)
  const pulseRef = useRef(0)
  const intensityRef = useRef(intensity)

  useEffect(() => {
    intensityRef.current = intensity
  }, [intensity])

  useFrame((state, delta) => {
    if (!labelRef.current) return

    pulseRef.current += delta

    const distance = camera.position.distanceTo(labelRef.current.getWorldPosition(new THREE.Vector3()))
    const targetOpacity = alwaysVisible || distance < 6 ? 1 : 0
    opacityRef.current = THREE.MathUtils.lerp(opacityRef.current, targetOpacity * intensityRef.current, delta * 3)

    const targetScale = alwaysVisible ? 1 : (distance < 6 ? 1 : 0.5)
    scaleRef.current = THREE.MathUtils.lerp(scaleRef.current, targetScale, delta * 3)

    labelRef.current.lookAt(camera.position)
    labelRef.current.position.y = position[1] + Math.sin(pulseRef.current) * 0.03
    labelRef.current.scale.setScalar(scaleRef.current * size)

    // Text from @react-three/drei returns a Group, access material via children
    if (textRef.current) {
      textRef.current.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.opacity = opacityRef.current
        }
      })
    }
  })

  return (
    <group ref={labelRef} position={position}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2.2 * size, 0.5]} />
        <meshBasicMaterial
          color={0x0a0a14}
          transparent
          opacity={0.75}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0, 0.01]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2.15 * size, 0.45]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.9}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      <Text
        ref={textRef}
        position={[0, 0, 0.02]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.11 * size}
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

const FloatingLabelMemo = memo(FloatingLabelMesh)

export function FloatingLabels({ 
  intensity = 1,
  className,
  customLabels = [] 
}) {
  const labels = useMemo(() => [...FLOATING_LABELS, ...customLabels], [customLabels])

  return (
    <group className={className}>
      {labels.map((label, i) => (
        <FloatingLabelMemo
          key={i}
          label={label.label}
          position={label.position}
          color={label.color}
          size={label.size}
          intensity={intensity}
          alwaysVisible={i === 0}
        />
      ))}
    </group>
  )
}

export function StageLabels({ 
  nodes = [], 
  labels = [], 
  colors = [],
  intensity = 1,
  activeIndex = -1,
  className 
}) {
  return (
    <group className={className}>
      {nodes.map((pos, i) => (
        <FloatingLabelMemo
          key={`stage-${i}`}
          label={labels[i] || `Stage ${i + 1}`}
          position={pos}
          color={colors[i] || 0x8b8dff}
          size={0.8}
          intensity={intensity}
          alwaysVisible={i === activeIndex}
        />
      ))}
    </group>
  )
}

function TooltipMesh({ position, label, color, intensity, camera }) {
  const meshRef = useRef()
  const opacityRef = useRef(0)
  const textRef = useRef()

  useFrame((state, delta) => {
    if (!meshRef.current) return

    const distance = camera.position.distanceTo(meshRef.current.getWorldPosition(new THREE.Vector3()))
    const targetOpacity = distance < 4 ? 1 : 0
    opacityRef.current = THREE.MathUtils.lerp(opacityRef.current, targetOpacity * intensity, delta * 5)

    meshRef.current.lookAt(camera.position)

    // Update opacity on all meshes in the group
    meshRef.current.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material.opacity = opacityRef.current
      }
    })
  })

  return (
    <group ref={meshRef} position={position}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.8, 0.4]} />
        <meshBasicMaterial
          color={0x0a0a14}
          transparent
          opacity={0.8}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0, 0.01]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.75, 0.35]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.9}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Text
        ref={textRef}
        position={[0, 0, 0.02]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.1}
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

export function FeatureTooltips({
  positions = [],
  labels = [],
  colors = [],
  intensity = 1,
  visible = true,
  className
}) {
  const { camera } = useThree()

  return (
    <group className={className}>
      {visible && positions.map((pos, i) => (
        <TooltipMesh
          key={i}
          position={pos}
          label={labels[i]}
          color={colors[i] || 0x8b8dff}
          intensity={intensity}
          camera={camera}
        />
      ))}
    </group>
  )
}

export default FloatingLabels