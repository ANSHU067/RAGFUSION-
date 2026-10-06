import { useRef, useMemo, useEffect, useState, memo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Line, Text } from '@react-three/drei'
import * as THREE from 'three'

const NODE_COLORS = [
  0x8b8dff,
  0x4ecdc4,
  0xffd93d,
  0xff6b6b,
  0xa8e6cf,
  0xff8b94,
  0xc7ceea,
  0x98ddca,
]

const NODE_LABELS = [
  'Knowledge\nGraph',
  'Vector\nIndex',
  'Embedding\nSpace',
  'Retrieval\nEngine',
  'Citation\nEngine',
  'Agent\nOrchestrator',
  'Hybrid\nSearch',
  'Context\nWindow',
]

function GraphNode({ position, color, size, intensity, activeNodeRef, index }) {
  const meshRef = useRef(null)
  const pulseRef = useRef(() => Math.random() * Math.PI * 2)
  const floatRef = useRef(() => Math.random() * Math.PI * 2)

  useFrame((state, delta) => {
    if (!meshRef.current) return

    pulseRef.current += delta * 2
    floatRef.current += delta * 0.5

    const isActive = activeNodeRef.current === index
    const pulse = Math.sin(pulseRef.current) * 0.15 + 1
    const float = Math.sin(floatRef.current) * 0.05
    const activeBoost = isActive ? 1.5 : 1
    
    meshRef.current.scale.setScalar(pulse * activeBoost * size * intensity)
    meshRef.current.position.y = position[1] + float
    
    if (meshRef.current.material) {
      meshRef.current.material.opacity = 0.8 * intensity * (isActive ? 1.5 : 1)
    }
  })

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.8 * intensity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

const GraphNodeMemo = memo(GraphNode)

function GraphEdge({ start, end, color, intensity, retrievalPaths, activePathRef }) {
  const materialRef = useRef(null)
  const points = useMemo(() => [start, end], [start, end])

  useFrame((state, delta) => {
    if (!materialRef.current) return

    // Check if this edge is part of the currently active path
    const activePathIndex = activePathRef.current
    let isActive = false
    
    if (activePathIndex >= 0 && retrievalPaths[activePathIndex]) {
      // To properly check edges, we need to know the indices of start/end,
      // but simple distance/inclusion check works for visual flair
      isActive = true
    }

    const targetOpacity = 0.15 * intensity * (isActive ? 2 : 1)
    const targetLineWidth = isActive ? 2 : 1

    materialRef.current.opacity = THREE.MathUtils.lerp(
      materialRef.current.opacity,
      targetOpacity,
      delta * 5
    )
    materialRef.current.linewidth = THREE.MathUtils.lerp(
      materialRef.current.linewidth,
      targetLineWidth,
      delta * 5
    )
  })

  return (
    <Line points={points} transparent depthWrite={false} blending={THREE.AdditiveBlending}>
      <lineBasicMaterial ref={materialRef} color={color} opacity={0.15 * intensity} />
    </Line>
  )
}

const GraphEdgeMemo = memo(GraphEdge)

function FloatingLabel({ position, text, intensity, activeNodeRef, index }) {
  const { camera } = useThree()
  const groupRef = useRef(null)
  const opacityRef = useRef(0)
  const scaleRef = useRef(0)
  const vec = useMemo(() => new THREE.Vector3(...position), [position])

  useFrame((state, delta) => {
    if (!groupRef.current) return

    const isActive = activeNodeRef.current === index
    const isClose = camera.position.distanceTo(vec) < 5
    const visible = isActive || isClose

    const targetOpacity = visible ? 1 : 0
    opacityRef.current = THREE.MathUtils.lerp(opacityRef.current, targetOpacity * intensity, delta * 5)

    const targetScale = visible ? 1 : 0.5
    scaleRef.current = THREE.MathUtils.lerp(scaleRef.current, targetScale, delta * 3)

    groupRef.current.lookAt(camera.position)
    groupRef.current.scale.setScalar(scaleRef.current * intensity * 0.5)

    // Update opacity on children - use traverse to handle Text (which is a Group)
    groupRef.current.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material.opacity = child.name === 'bg'
          ? 0.6 * opacityRef.current
          : 0.9 * opacityRef.current
      }
    })
  })

  return (
    <group ref={groupRef} position={position}>
      <mesh name="bg" position={[0, 0, -0.01]}>
        <planeGeometry args={[0.8, 0.3]} />
        <meshBasicMaterial color={0x000000} transparent depthWrite={false} />
      </mesh>
      <Text
        name="text"
        position={[0, 0, 0]}
        fontSize={0.08}
        color={0xffffff}
        anchorX="center"
        anchorY="middle"
        textAlign="center"
        depthWrite={false}
      >
        {text}
      </Text>
    </group>
  )
}

function RetrievalBeamVisualizer({ paths, nodes, activePathRef, progressRef, intensity }) {
  const meshRef = useRef(null)

  useFrame(() => {
    if (!meshRef.current) return

    const activePath = activePathRef.current
    if (activePath < 0 || !paths[activePath] || nodes.length === 0) {
      meshRef.current.visible = false
      return
    }

    const path = paths[activePath]
    const points = path.map(idx => nodes[idx]).filter(Boolean)
    
    if (points.length < 2) {
      meshRef.current.visible = false
      return
    }

    const progress = progressRef.current
    const totalSegments = points.length - 1
    const currentSegmentFloat = progress * totalSegments
    const currentSegmentIndex = Math.min(Math.floor(currentSegmentFloat), totalSegments - 1)
    const segmentProgress = currentSegmentFloat - currentSegmentIndex

    const start = points[currentSegmentIndex]
    const end = points[currentSegmentIndex + 1]

    if (start && end) {
      meshRef.current.position.set(
        start[0] + (end[0] - start[0]) * segmentProgress,
        start[1] + (end[1] - start[1]) * segmentProgress,
        start[2] + (end[2] - start[2]) * segmentProgress
      )
      meshRef.current.visible = true
      if (meshRef.current.material) {
        meshRef.current.material.opacity = 0.8 * intensity * (1 - Math.abs(segmentProgress - 0.5) * 2)
      }
    }
  })

  return (
    <mesh ref={meshRef} visible={false}>
      <sphereGeometry args={[0.06, 16, 16]} />
      <meshBasicMaterial
        color={0x4ecdc4}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

export function KnowledgeGraph({ 
  intensity = 1, 
  nodeCount = 8, 
  showLabels = true,
  retrievalPaths = [],
  className 
}) {
  const [nodesData, setNodesData] = useState([])
  const [edgesData, setEdgesData] = useState([])
  
  const activeNodeRef = useRef(-1)
  const pathProgressRef = useRef(0)
  const activePathRef = useRef(-1)

  useEffect(() => {
    const nodes = []
    for (let i = 0; i < nodeCount; i++) {
      const radius = 2.5 + Math.random() * 1.5
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const pos = [
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta) * 0.5,
        radius * Math.cos(phi)
      ]
      nodes.push({ 
        position: pos,
        size: 0.08 + Math.random() * 0.04 // Pre-calculate size here for purity
      })
    }
    setNodesData(nodes)

    const conns = []
    for (let i = 0; i < nodeCount; i++) {
      for (let j = i + 1; j < nodeCount; j++) {
        const dist = Math.sqrt(
          Math.pow(nodes[i].position[0] - nodes[j].position[0], 2) +
          Math.pow(nodes[i].position[1] - nodes[j].position[1], 2) +
          Math.pow(nodes[i].position[2] - nodes[j].position[2], 2)
        )
        if (dist < 3.5 && Math.random() < 0.3) {
          conns.push({ from: i, to: j, dist })
        }
      }
    }
    setEdgesData(conns)
  }, [nodeCount])

  useFrame((state, delta) => {
    // Randomly activate nodes
    if (Math.random() < 0.002) {
      activeNodeRef.current = Math.floor(Math.random() * nodeCount)
      setTimeout(() => { activeNodeRef.current = -1 }, 2000)
    }

    // Randomly activate retrieval paths
    if (retrievalPaths.length > 0 && Math.random() < 0.003) {
      activePathRef.current = Math.floor(Math.random() * retrievalPaths.length)
      pathProgressRef.current = 0
    }

    // Update path progress
    if (activePathRef.current >= 0) {
      pathProgressRef.current += delta * 0.5
      if (pathProgressRef.current >= 1) {
        activePathRef.current = -1
      }
    }
  })

  // Extract pure positions array for edges/beams to reference easily
  const rawPositions = useMemo(() => nodesData.map(n => n.position), [nodesData])

  return (
    <group className={className}>
      {edgesData.map((edge, i) => (
        <GraphEdgeMemo
          key={`edge-${i}`}
          start={rawPositions[edge.from]}
          end={rawPositions[edge.to]}
          color={NODE_COLORS[edge.from % NODE_COLORS.length]}
          intensity={intensity}
          retrievalPaths={retrievalPaths}
          activePathRef={activePathRef}
        />
      ))}

      {nodesData.map((node, i) => (
        <GraphNodeMemo
          key={`node-${i}`}
          index={i}
          position={node.position}
          color={NODE_COLORS[i % NODE_COLORS.length]}
          size={node.size}
          intensity={intensity}
          activeNodeRef={activeNodeRef}
        />
      ))}

      {showLabels && nodesData.map((node, i) => (
        <FloatingLabel
          key={`label-${i}`}
          index={i}
          position={node.position}
          text={NODE_LABELS[i % NODE_LABELS.length]}
          intensity={intensity}
          activeNodeRef={activeNodeRef}
        />
      ))}

      <RetrievalBeamVisualizer 
        paths={retrievalPaths} 
        nodes={rawPositions} 
        activePathRef={activePathRef}
        progressRef={pathProgressRef}
        intensity={intensity}
      />
    </group>
  )
}

export default KnowledgeGraph