import { useRef, useMemo, memo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import * as THREE from 'three'

const GLASS_FEATURES = [
  { title: 'Hybrid Search', subtitle: 'Semantic + keyword', icon: '🔍', color: 0x8b8dff },
  { title: 'Citation Ready', subtitle: 'Every answer traced', icon: '📎', color: 0x4ecdc4 },
  { title: 'Multi-Agent', subtitle: 'Specialized AI', icon: '🤖', color: 0xff6b9d },
  { title: 'OCR & Vision', subtitle: 'Scan to knowledge', icon: '👁️', color: 0xffd93d },
  { title: 'Knowledge Graph', subtitle: 'Connected sources', icon: '🕸️', color: 0x6bcb77 },
  { title: 'Vector Search', subtitle: 'Semantic retrieval', icon: '🎯', color: 0x4d96ff },
  { title: 'Secure Workspace', subtitle: 'Enterprise controls', icon: '🔒', color: 0xa855f7 },
  { title: 'Real-time Sync', subtitle: 'Live updates', icon: '⚡', color: 0x06b6d4 },
]

function GlassCardMesh({ 
  feature, 
  position, 
  rotation = [0, 0, 0], 
  scale = 1,
  intensity = 1,
  index,
  onHover 
}) {
  const { camera } = useThree()
  const cardRef = useRef()
  const glowMeshRef = useRef()
  const hoverRef = useRef(false)
  const pulseRef = useRef(0)
  const targetScale = useRef(scale)
  const currentScale = useRef(scale)
  const hoverScaleRef = useRef(1)

  useFrame((state, delta) => {
    pulseRef.current += delta

    currentScale.current = THREE.MathUtils.lerp(currentScale.current, targetScale.current, delta * 5)

    if (cardRef.current) {
      cardRef.current.scale.setScalar(currentScale.current)
      cardRef.current.rotation.y += delta * 0.015
      cardRef.current.position.y = position[1] + Math.sin(pulseRef.current + index) * 0.04

      const distance = camera.position.distanceTo(cardRef.current.getWorldPosition(new THREE.Vector3()))
      if (distance < 4 && !hoverRef.current) {
        hoverRef.current = true
        targetScale.current = scale * 1.08
        hoverScaleRef.current = 1.15
        onHover?.(true, index)
      } else if (distance >= 4 && hoverRef.current) {
        hoverRef.current = false
        targetScale.current = scale
        hoverScaleRef.current = 1
        onHover?.(false, index)
      }
    }

    if (glowMeshRef.current) {
      glowMeshRef.current.scale.setScalar(hoverScaleRef.current)
    }
  })

  const cardWidth = 1.6
  const cardHeight = 1.1

  return (
    <group ref={cardRef} position={position} rotation={rotation}>
      <mesh position={[0, 0, 0.01]}>
        <boxGeometry args={[cardWidth, cardHeight, 0.06]} />
        <meshPhysicalMaterial
          color={0xffffff}
          transparent
          opacity={0.1 * intensity}
          transmission={0.92}
          roughness={0.02}
          metalness={0}
          clearcoat={1}
          clearcoatRoughness={0.02}
          ior={1.5}
          thickness={0.08}
          transmissionColor={new THREE.Color(feature.color)}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0, 0.04]}>
        <planeGeometry args={[cardWidth - 0.08, cardHeight - 0.08]} />
        <meshBasicMaterial
          color={0x0a0a14}
          transparent
          opacity={0.65 * intensity}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 0.3, 0.06]}>
        <planeGeometry args={[0.55, 0.55]} />
        <meshBasicMaterial
          color={feature.color}
          transparent
          opacity={0.9 * intensity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      <Text position={[0, 0.3, 0.07]} fontSize={0.22} anchorX="center" anchorY="middle" color={feature.color} depthWrite={false}>
        {feature.icon}
      </Text>

      <mesh position={[0, 0.02, 0.06]}>
        <planeGeometry args={[1.35, 0.28]} />
        <meshBasicMaterial
          color={0xffffff}
          transparent
          opacity={0.9 * intensity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      <Text position={[0, 0.02, 0.07]} fontSize={0.12} color={0x0a0a14} anchorX="center" anchorY="middle" depthWrite={false}>
        {feature.title}
      </Text>

      <mesh position={[0, -0.22, 0.06]}>
        <planeGeometry args={[1.35, 0.22]} />
        <meshBasicMaterial
          color={feature.color}
          transparent
          opacity={0.8 * intensity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      <Text position={[0, -0.22, 0.07]} fontSize={0.09} color={0x0a0a14} anchorX="center" anchorY="middle" depthWrite={false}>
        {feature.subtitle}
      </Text>

      <mesh position={[0, -0.42, 0.06]} scale={0.28}>
        <planeGeometry args={[1.8, 0.025]} />
        <meshBasicMaterial
          color={feature.color}
          transparent
          opacity={0.4 * intensity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      <mesh ref={glowMeshRef}>
        <sphereGeometry args={[0.9, 16, 16]} />
        <meshBasicMaterial
          color={feature.color}
          transparent
          opacity={0.03 * intensity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}

const GlassCardMemo = memo(GlassCardMesh)

export function GlassCards({ 
  count = 6, 
  radius = 4.5, 
  intensity = 1,
  className,
  onCardHover 
}) {
  const cards = useMemo(() => {
    const result = []
    for (let i = 0; i < count; i++) {
      const feature = GLASS_FEATURES[i % GLASS_FEATURES.length]
      const angle = (i / count) * Math.PI * 2 - Math.PI / 2
      const y = Math.sin(angle * 0.5) * 1.2
      const r = radius + Math.cos(angle) * 0.3
      result.push({
        feature,
        position: [Math.cos(angle) * r, y, Math.sin(angle) * r],
        rotation: [0, angle + Math.PI / 2, 0],
        scale: 0.9 + (i % 3) * 0.05,
        index: i,
      })
    }
    return result
  }, [count, radius])

  return (
    <group className={className}>
      {cards.map((card, i) => (
        <GlassCardMemo
          key={i}
          feature={card.feature}
          position={card.position}
          rotation={card.rotation}
          scale={card.scale}
          intensity={intensity}
          index={card.index}
          onHover={onCardHover}
        />
      ))}
    </group>
  )
}

export default GlassCards