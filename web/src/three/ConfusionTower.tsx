// Held-out confusion matrix as extruded columns: height = number of test comments, darker = larger share of the true class.
import { Html } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, useState } from 'react'
import * as THREE from 'three'
import { reducedMotion } from '../lib/motion'
import { useApp } from '../lib/store'
import { THREE_PALETTE } from './palette'

function Columns({ cm, labels, onHover }: { cm: number[][]; labels: string[]; onHover: (s: string | null) => void }) {
  const theme = useApp((s) => s.theme)
  const pal = THREE_PALETTE[theme]
  const group = useRef<THREE.Group>(null)
  const grown = useRef(0)
  const still = reducedMotion()
  const max = Math.max(1, ...cm.flat())
  const n = labels.length
  const gap = 1.25

  useFrame((_, delta) => {
    if (!group.current) return
    grown.current = still ? 1 : Math.min(1, grown.current + delta * 0.9)
    const e = 1 - Math.pow(1 - grown.current, 3)
    group.current.children.forEach((child) => {
      if ((child as THREE.Mesh).isMesh && child.userData.h) {
        child.scale.y = Math.max(0.001, e)
        child.position.y = (child.userData.h * e) / 2
      }
    })
    if (!still) group.current.rotation.y = Math.sin(performance.now() / 6000) * 0.25 - 0.5
  })

  const color = new THREE.Color()
  return (
    <group ref={group} rotation={[0, -0.5, 0]} position={[0, -1.2, 0]}>
      {cm.map((row, i) => {
        const rowTotal = Math.max(1, row.reduce((a, b) => a + b, 0))
        return row.map((v, j) => {
          const h = Math.max(0.04, (v / max) * 3)
          const share = v / rowTotal
          const c = color.set(pal.bg).lerp(new THREE.Color(pal.brand), 0.25 + 0.75 * share).getHex()
          const x = (j - (n - 1) / 2) * gap
          const z = (i - (n - 1) / 2) * gap
          return (
            <mesh
              key={`${i}-${j}`}
              position={[x, h / 2, z]}
              userData={{ h }}
              onPointerOver={(e) => {
                e.stopPropagation()
                onHover(`True ${labels[i]}, predicted ${labels[j]}: ${v} comments (${Math.round(share * 100)}% of true ${labels[i]})`)
              }}
              onPointerOut={() => onHover(null)}
            >
              <boxGeometry args={[0.9, h, 0.9]} />
              <meshStandardMaterial color={c} roughness={0.8} />
            </mesh>
          )
        })
      })}
      {labels.map((l, j) => (
        <Html key={`p${l}`} position={[(j - (n - 1) / 2) * gap, 0, ((n - 1) / 2) * gap + 0.95]} center zIndexRange={[10, 0]}>
          <span className="label" style={{ whiteSpace: 'nowrap' }}>pred. {l}</span>
        </Html>
      ))}
      {labels.map((l, i) => (
        <Html key={`t${l}`} position={[-((n - 1) / 2) * gap - 1.25, 0, (i - (n - 1) / 2) * gap]} center zIndexRange={[10, 0]}>
          <span className="label" style={{ whiteSpace: 'nowrap', color: 'var(--text)' }}>true {l}</span>
        </Html>
      ))}
    </group>
  )
}

export function ConfusionTower({ cm, labels }: { cm: number[][]; labels: string[] }) {
  const [hover, setHover] = useState<string | null>(null)
  return (
    <div>
      <div className="stage" style={{ aspectRatio: '1.3 / 1' }} data-testid="confusion-3d">
        <Canvas camera={{ position: [4.6, 4.2, 6.2], fov: 40 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}
          onCreated={({ camera }) => camera.lookAt(0, 0, 0)}>
          <ambientLight intensity={1.5} />
          <directionalLight position={[5, 8, 4]} intensity={1.5} />
          <Columns cm={cm} labels={labels} onHover={setHover} />
        </Canvas>
      </div>
      <div className="stage-caption" aria-live="polite">
        <span>{hover ?? 'Hover a column for its count. Taller means more test comments; darker means a larger share of that true class.'}</span>
      </div>
    </div>
  )
}
