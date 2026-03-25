import { useRef, useMemo } from 'react'
import { useFrame, Canvas } from '@react-three/fiber'
import { Float, Sphere, Stars } from '@react-three/drei'
import * as THREE from 'three'

// Lat/long to xyz on unit sphere (y-up)
function latLongToXYZ(lat, long, r = 1) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (long + 180) * (Math.PI / 180)
  return [
    r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  ]
}

// Arc between two points on sphere (curved outward)
function arcPoints(p1, p2, segments = 24) {
  const mid = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2]
  const len = Math.sqrt(mid[0] ** 2 + mid[1] ** 2 + mid[2] ** 2)
  const bulge = 0.4
  const scaled = mid.map((c) => (c / len) * (1 + bulge))
  const points = []
  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const ct = 1 - t
    const x = ct * ct * p1[0] + 2 * ct * t * scaled[0] + t * t * p2[0]
    const y = ct * ct * p1[1] + 2 * ct * t * scaled[1] + t * t * p2[1]
    const z = ct * ct * p1[2] + 2 * ct * t * scaled[2] + t * t * p2[2]
    points.push(new THREE.Vector3(x, y, z))
  }
  return points
}

// Fixed seed for consistent "random" node positions (global clients/customers)
const NODES = [
  [37.7, -122.4],   // SF
  [51.5, -0.1],     // London
  [35.6, 139.6],    // Tokyo
  [40.7, -74.0],    // NYC
  [19.0, 72.8],     // Mumbai
  [-33.8, 151.2],   // Sydney
  [-23.5, -46.6],   // São Paulo
  [52.5, 13.4],     // Berlin
  [25.0, 121.5],    // Taipei
  [1.3, 103.8],     // Singapore
  [55.7, 12.5],     // Copenhagen
  [28.5, 77.0],     // Delhi
]

const CONNECTIONS = [
  [0, 1], [0, 3], [1, 2], [2, 9], [3, 4], [4, 6], [5, 9], [6, 7], [7, 8], [8, 2],
  [0, 2], [1, 7], [3, 4], [5, 6], [9, 10], [10, 11], [4, 11],
]

function GlobeMesh() {
  const meshRef = useRef()
  const radius = 1.15

  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.15
  })

  const nodePositions = useMemo(() => NODES.map(([lat, long]) => latLongToXYZ(lat, long, radius)), [])

  const arcGeometries = useMemo(() => {
    return CONNECTIONS.map(([i, j]) => {
      const pts = arcPoints(nodePositions[i], nodePositions[j])
      return new THREE.BufferGeometry().setFromPoints(pts)
    })
  }, [nodePositions])

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.4}>
      <group>
        {/* Globe wireframe (latitude/longitude grid) */}
        <Sphere ref={meshRef} args={[radius, 32, 24]}>
          <meshBasicMaterial
            color="#1e293b"
            wireframe
            transparent
            opacity={0.6}
          />
        </Sphere>
        {/* Inner glow */}
        <Sphere args={[radius - 0.02, 32, 24]}>
          <meshStandardMaterial
            color="#0f172a"
            transparent
            opacity={0.85}
            roughness={0.9}
            metalness={0.1}
          />
        </Sphere>
        {/* Connection arcs - client/customer links */}
        {arcGeometries.map((geom, i) => (
          <line key={i} geometry={geom}>
            <lineBasicMaterial
              color={i % 3 === 0 ? '#6366f1' : i % 3 === 1 ? '#22d3ee' : '#818cf8'}
              transparent
              opacity={0.7}
              linewidth={1}
            />
          </line>
        ))}
        {/* Node points - clients/customers */}
        {nodePositions.map((pos, i) => (
          <Sphere key={i} args={[0.035, 12, 12]} position={pos}>
            <meshBasicMaterial color="#22d3ee" />
          </Sphere>
        ))}
      </group>
    </Float>
  )
}

export default function Scene3D() {
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <pointLight position={[-10, -10, -5]} color="#22d3ee" intensity={0.6} />
        <pointLight position={[0, 5, 2]} color="#6366f1" intensity={0.4} />
        <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
        <GlobeMesh />
      </Canvas>
    </div>
  )
}
