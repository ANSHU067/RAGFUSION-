import { useMemo } from 'react'
import * as THREE from 'three'

export function Lights() {
  const ambientLight = useMemo(() => new THREE.Color(0xffffff), [])
  const directionalColor = useMemo(() => new THREE.Color(0xffffff), [])
  const pointLightColor = useMemo(() => new THREE.Color(0x8b8dff), [])
  const rimLightColor = useMemo(() => new THREE.Color(0xff6b9d), [])
  const fillLightColor = useMemo(() => new THREE.Color(0x4ecdc4), [])

  return (
    <>
      <ambientLight color={ambientLight} intensity={0.35} />
      
      <directionalLight
        color={directionalColor}
        intensity={1.2}
        position={[5, 10, 7.5]}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-near={0.1}
        shadow-camera-far={50}
        shadow-camera-left={-15}
        shadow-camera-right={15}
        shadow-camera-top={15}
        shadow-camera-bottom={-15}
        shadow-bias={-0.0001}
      />
      
      <pointLight
        color={pointLightColor}
        intensity={40}
        position={[0, 3, 5]}
        distance={20}
        decay={2}
      />
      
      <pointLight
        color={fillLightColor}
        intensity={25}
        position={[-5, -2, 3]}
        distance={15}
        decay={2}
      />
      
      <pointLight
        color={rimLightColor}
        intensity={30}
        position={[5, -3, -5]}
        distance={20}
        decay={2}
      />
      
      <pointLight
        color={0xffffff}
        intensity={15}
        position={[0, -5, 0]}
        distance={15}
        decay={2}
      />
    </>
  )
}

export default Lights