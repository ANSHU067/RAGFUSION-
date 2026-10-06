import { useMemo } from 'react'
import * as THREE from 'three'

export function Environment({ children }) {
  const texture = useMemo(() => {
    const size = 512
    const data = new Uint8Array(size * size * 4)
    
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const i = (y * size + x) * 4
        const u = x / size
        const v = y / size
        
        const theta = u * Math.PI * 2
        const phi = v * Math.PI
        
        const sinPhi = Math.sin(phi)
        const cosPhi = Math.cos(phi)
        const sinTheta = Math.sin(theta)
        const cosTheta = Math.cos(theta)
        
        const dirX = sinPhi * cosTheta
        const dirY = cosPhi
        const dirZ = sinPhi * sinTheta
        
        const horizon = 1 - Math.max(0, dirY)
        const sunDot = Math.max(0, dirX * 0.3 + dirY * 0.8 + dirZ * 0.5)
        
        const skyColor = new THREE.Color(0x1a1a2e)
        const horizonColor = new THREE.Color(0x8b8dff)
        const groundColor = new THREE.Color(0x0a0a14)
        const sunColor = new THREE.Color(0xffd93d)
        const rimColor = new THREE.Color(0x4ecdc4)
        
        let color = new THREE.Color()
          .copy(skyColor)
          .lerp(horizonColor, horizon * 0.5)
          .lerp(groundColor, Math.max(0, -dirY) * 0.3)
        
        color.add(sunColor.clone().multiplyScalar(Math.pow(sunDot, 32) * 2))
        color.add(rimColor.clone().multiplyScalar(Math.max(0, -dirY) * 0.1))
        
        data[i] = Math.round(color.r * 255)
        data[i + 1] = Math.round(color.g * 255)
        data[i + 2] = Math.round(color.b * 255)
        data[i + 3] = 255
      }
    }
    
    const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat)
    tex.mapping = THREE.EquirectangularReflectionMapping
    tex.needsUpdate = true
    return tex
  }, [])

  return (
    <>
      <mesh scale={[-1, 1, 1]}>
        <sphereGeometry args={[50, 32, 32]} />
        <meshBasicMaterial map={texture} side={THREE.BackSide} />
      </mesh>
      {children}
    </>
  )
}

export function StudioEnvironment({ children }) {
  return <Environment>{children}</Environment>
}

export default Environment
