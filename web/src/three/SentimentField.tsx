// Every review as a block in 3D space: x = sentiment score (P(pos) - P(neg)), y = model confidence,
// z = the teaching aspect it mentions most confidently. Built from the active dataset, not decoration.
import { Canvas, useFrame, type ThreeEvent } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import type { Overview } from '../lib/api'
import { reducedMotion, ScrollTrigger } from '../lib/motion'
import { useApp } from '../lib/store'
import { THREE_PALETTE } from './palette'

type Point = Overview['points'][number]

const W = 6 // x extent
const H = 3.2 // y extent
const D = 4.4 // z extent

function Field({ points, lanes, progress, onHover, onPick }: {
  points: Point[]
  lanes: string[]
  progress: { current: number }
  onHover: (p: Point | null) => void
  onPick: (p: Point) => void
}) {
  const theme = useApp((s) => s.theme)
  const pal = THREE_PALETTE[theme]
  const mesh = useRef<THREE.InstancedMesh>(null)
  const group = useRef<THREE.Group>(null)
  const hovered = useRef<number | null>(null)
  const still = reducedMotion()

  const layout = useMemo(() => {
    const laneIndex = new Map(lanes.map((l, i) => [l, i]))
    const counts = new Map<string, number>()
    return points.map((p) => {
      const lane = laneIndex.get(p.aspect ?? '__none') ?? lanes.length - 1
      const key = `${lane}:${Math.round(p.score * 20)}:${Math.round(p.confidence * 10)}`
      const n = counts.get(key) ?? 0
      counts.set(key, n + 1)
      const x = (p.score / 2) * W + (n % 2 ? 0.07 : -0.07) * Math.ceil(n / 2)
      const y = ((p.confidence - 0.3) / 0.7) * H - H / 2
      const z = lanes.length > 1 ? (lane / (lanes.length - 1)) * D - D / 2 : 0
      return new THREE.Vector3(x, Math.max(-H / 2, y), z)
    })
  }, [points, lanes])

  useEffect(() => {
    const m = mesh.current
    if (!m) return
    const dummy = new THREE.Object3D()
    const color = new THREE.Color()
    layout.forEach((pos, i) => {
      dummy.position.copy(pos)
      dummy.scale.setScalar(1)
      dummy.updateMatrix()
      m.setMatrixAt(i, dummy.matrix)
      m.setColorAt(i, color.set(pal[points[i].sentiment] ?? pal.text))
    })
    m.instanceMatrix.needsUpdate = true
    if (m.instanceColor) m.instanceColor.needsUpdate = true
  }, [layout, points, pal])

  const frame = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const x0 = -W / 2, x1 = W / 2, y0 = -H / 2, y1 = H / 2, z0 = -D / 2, z1 = D / 2
    const v = [
      x0, y0, z0, x1, y0, z0, x0, y0, z1, x1, y0, z1, x0, y0, z0, x0, y0, z1, x1, y0, z0, x1, y0, z1,
      0, y0, z0, 0, y0, z1, // the neutral line (score 0)
      x0, y0, z0, x0, y1, z0, x1, y0, z0, x1, y1, z0,
    ]
    g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3))
    return g
  }, [])

  useFrame((_, delta) => {
    const g = group.current
    if (!g) return
    const target = -0.55 + progress.current * 1.3
    if (still) g.rotation.y = -0.35
    else {
      g.rotation.y += (target - g.rotation.y) * Math.min(1, delta * 3) + delta * 0.03
      g.rotation.x = 0.22 + progress.current * 0.12
    }
  })

  const setScale = (id: number | null, s: number) => {
    const m = mesh.current
    if (!m || id === null || !layout[id]) return
    const dummy = new THREE.Object3D()
    dummy.position.copy(layout[id])
    dummy.scale.setScalar(s)
    dummy.updateMatrix()
    m.setMatrixAt(id, dummy.matrix)
    m.instanceMatrix.needsUpdate = true
  }

  const move = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    const id = e.instanceId ?? null
    if (id === hovered.current) return
    setScale(hovered.current, 1)
    hovered.current = id
    setScale(id, 1.7)
    onHover(id === null ? null : points[id])
    document.body.style.cursor = id === null ? '' : 'pointer'
  }
  const leave = () => {
    setScale(hovered.current, 1)
    hovered.current = null
    onHover(null)
    document.body.style.cursor = ''
  }

  return (
    <group ref={group} rotation={[0.22, -0.55, 0]}>
      <lineSegments geometry={frame}>
        <lineBasicMaterial color={pal.rule} />
      </lineSegments>
      <instancedMesh
        ref={mesh}
        args={[undefined, undefined, points.length]}
        onPointerMove={move}
        onPointerOut={leave}
        onClick={(e) => e.instanceId !== undefined && onPick(points[e.instanceId])}
      >
        <boxGeometry args={[0.11, 0.11, 0.11]} />
        <meshStandardMaterial roughness={0.75} metalness={0} />
      </instancedMesh>
    </group>
  )
}

export function SentimentField({ data, laneLabels, onPick }: {
  data: Overview['points']
  laneLabels: Record<string, string>
  onPick: (id: number) => void
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const progress = useRef(0)
  const [hover, setHover] = useState<Point | null>(null)
  const [visible, setVisible] = useState(true)
  const lanes = useMemo(() => {
    const present = Array.from(new Set(data.map((p) => p.aspect).filter(Boolean))) as string[]
    const order = Object.keys(laneLabels)
    present.sort((a, b) => order.indexOf(a) - order.indexOf(b))
    return [...present, '__none']
  }, [data, laneLabels])

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const st = ScrollTrigger.create({
      trigger: el,
      start: 'top bottom',
      end: 'bottom top',
      onUpdate: (self) => {
        progress.current = self.progress
      },
    })
    const io = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0 })
    io.observe(el)
    return () => {
      st.kill()
      io.disconnect()
    }
  }, [])

  return (
    <div>
      <div className="stage" ref={wrap} data-testid="sentiment-field">
        <Canvas
          frameloop={visible ? 'always' : 'never'}
          camera={{ position: [0, 1.4, 8.2], fov: 42 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
          aria-label="Three-dimensional view of every review by sentiment, confidence and aspect"
        >
          <ambientLight intensity={1.6} />
          <directionalLight position={[4, 6, 5]} intensity={1.4} />
          <Field points={data} lanes={lanes} progress={progress} onHover={setHover} onPick={(p) => onPick(p.id)} />
        </Canvas>
        <span className="axis-note" style={{ left: 14, bottom: 12 }}>Negative</span>
        <span className="axis-note" style={{ right: 14, bottom: 12 }}>Positive</span>
        <span className="axis-note" style={{ left: 14, top: 12 }}>Height: model confidence</span>
        <span className="axis-note" style={{ right: 14, top: 12 }}>Depth: aspect</span>
      </div>
      <div className="stage-caption" aria-live="polite">
        {hover ? (
          <>
            <span>
              <strong style={{ color: 'var(--text)' }}>Review #{hover.id}</strong> · {hover.sentiment} · confidence {Math.round(hover.confidence * 100)}% ·{' '}
              {hover.aspect ? laneLabels[hover.aspect] : 'no aspect detected'}
            </span>
            <span>Click to read it</span>
          </>
        ) : (
          <>
            <span>{data.length} reviews, one block each. Scroll to turn the field; hover a block to identify it.</span>
            <span>{lanes.length - 1} aspect lanes</span>
          </>
        )}
      </div>
    </div>
  )
}
