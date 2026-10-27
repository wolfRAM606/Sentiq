// Held-out confusion matrix as extruded columns: height = number of test comments, darker = larger share of the true class.
// Axis labels are ordinary HTML elements positioned every frame by projecting their 3D anchor points.
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useRef, useState } from 'react'
import * as THREE from 'three'
import { reducedMotion } from '../lib/motion'
import { useApp } from '../lib/store'
import { THREE_PALETTE } from './palette'

const GAP = 1.25

interface Anchor {
  text: string
  pos: [number, number, number]
  strong?: boolean
}

function Columns({ cm, labels, anchors, labelEls, onHover }: {
  cm: number[][]
  labels: string[]
  anchors: Anchor[]
  labelEls: { current: (HTMLSpanElement | null)[] }
  onHover: (s: string | null) => void
}) {
  const theme = useApp((s) => s.theme)
  const pal = THREE_PALETTE[theme]
  const group = useRef<THREE.Group>(null)
  const grown = useRef(0)
  const still = reducedMotion()
  const { camera, size } = useThree()
  const max = Math.max(1, ...cm.flat())
  const n = labels.length
  const v = new THREE.Vector3()

  useFrame((_, delta) => {
    const g = group.current
    if (!g) return
    grown.current = still ? 1 : Math.min(1, grown.current + delta * 0.9)
    const e = 1 - Math.pow(1 - grown.current, 3)
    g.children.forEach((child) => {
      if ((child as THREE.Mesh).isMesh && child.userData.h) {
        child.scale.y = Math.max(0.001, e)
        child.position.y = (child.userData.h * e) / 2
      }
    })
    if (!still) g.rotation.y = Math.sin(performance.now() / 7000) * 0.12 - 0.18
    g.updateMatrixWorld()
    anchors.forEach((a, i) => {
      const el = labelEls.current[i]
      if (!el) return
      v.set(...a.pos)
      g.localToWorld(v)
      v.project(camera)
      el.style.transform = `translate(-50%, -50%) translate(${((v.x + 1) / 2) * size.width}px, ${((1 - v.y) / 2) * size.height}px)`
      el.style.opacity = v.z < 1 ? '1' : '0'
    })
  })

  const color = new THREE.Color()
  return (
    <group ref={group} rotation={[0, -0.18, 0]} position={[0.4, -0.55, -0.3]}>
      {cm.map((row, i) => {
        const rowTotal = Math.max(1, row.reduce((a, b) => a + b, 0))
        return row.map((val, j) => {
          const h = Math.max(0.04, (val / max) * 3)
          const share = val / rowTotal
          const c = color.set(pal.bg).lerp(new THREE.Color(pal.brand), 0.25 + 0.75 * share).getHex()
          return (
            <mesh
              key={`${i}-${j}`}
              position={[(j - (n - 1) / 2) * GAP, h / 2, (i - (n - 1) / 2) * GAP]}
              userData={{ h }}
              onPointerOver={(ev) => {
                ev.stopPropagation()
                onHover(`True ${labels[i]}, predicted ${labels[j]}: ${val} comments (${Math.round(share * 100)}% of true ${labels[i]})`)
              }}
              onPointerOut={() => onHover(null)}
            >
              <boxGeometry args={[0.9, h, 0.9]} />
              <meshStandardMaterial color={c} roughness={0.8} />
            </mesh>
          )
        })
      })}
    </group>
  )
}

export function ConfusionTower({ cm, labels }: { cm: number[][]; labels: string[] }) {
  const [hover, setHover] = useState<string | null>(null)
  const labelEls = useRef<(HTMLSpanElement | null)[]>([])
  const n = labels.length
  const anchors: Anchor[] = [
    ...labels.map((l, j) => ({ text: `pred. ${l}`, pos: [(j - (n - 1) / 2) * GAP, 0, ((n - 1) / 2) * GAP + 1.05] as [number, number, number] })),
    ...labels.map((l, i) => ({ text: `true ${l}`, pos: [-((n - 1) / 2) * GAP - 1.55, 0, (i - (n - 1) / 2) * GAP] as [number, number, number], strong: true })),
  ]
  return (
    <div>
      <div className="stage" style={{ aspectRatio: '1.3 / 1', overflow: 'hidden' }} data-testid="confusion-3d">
        <Canvas camera={{ position: [0.8, 5.4, 6.4], fov: 40 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}
          onCreated={({ camera }) => camera.lookAt(0, 0, 0)}>
          <ambientLight intensity={1.5} />
          <directionalLight position={[5, 8, 4]} intensity={1.5} />
          <Columns cm={cm} labels={labels} anchors={anchors} labelEls={labelEls} onHover={setHover} />
        </Canvas>
        {anchors.map((a, i) => (
          <span
            key={a.text}
            ref={(el) => {
              labelEls.current[i] = el
            }}
            className="label"
            data-axis-label
            style={{ position: 'absolute', left: 0, top: 0, whiteSpace: 'nowrap', pointerEvents: 'none', color: a.strong ? 'var(--text)' : undefined }}
          >
            {a.text}
          </span>
        ))}
      </div>
      <div className="stage-caption" aria-live="polite">
        <span>{hover ?? 'Hover a column for its count. Taller means more test comments; darker means a larger share of that true class.'}</span>
      </div>
    </div>
  )
}
