import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

const COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#ef4444', '#f59e0b', '#06b6d4']

export default function TrustChart({ trustHistory }) {
  const svgRef = useRef(null)

  const clientIds = Object.keys(trustHistory || {})
  if (clientIds.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="log"
        style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}
      >
        No trust history yet. Run clients and click Aggregate.
      </motion.div>
    )
  }

  const maxRounds = Math.max(...clientIds.map((cid) => (trustHistory[cid] || []).length), 1)
  const W = 800
  const H = 260
  const padL = 48
  const padR = 20
  const padT = 18
  const padB = 34
  const plotW = W - padL - padR
  const plotH = H - padT - padB
  const yMin = 0
  const yMax = 100

  const xAt = (i) => padL + (maxRounds === 1 ? plotW / 2 : (i / (maxRounds - 1)) * plotW)
  const yAt = (v) => {
    const t = (v - yMin) / (yMax - yMin)
    return padT + (1 - t) * plotH
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{ width: '100%', overflow: 'hidden' }}
    >
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 260 }}>
        {[...Array(5)].map((_, k) => (
          <line
            key={k}
            x1={padL}
            x2={padL + plotW}
            y1={padT + (k / 4) * plotH}
            y2={padT + (k / 4) * plotH}
            stroke="rgba(148, 163, 184, 0.15)"
            strokeWidth="1"
          />
        ))}
        {clientIds.map((cid, idx) => {
          const vals = trustHistory[cid] || []
          const color = COLORS[idx % COLORS.length]
          const points = vals.map((v, i) => `${xAt(i)},${yAt(v)}`).join(' ')
          return (
            <g key={cid}>
              <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth="2"
              />
              {vals.length > 0 && (
                <circle
                  cx={xAt(vals.length - 1)}
                  cy={yAt(vals[vals.length - 1])}
                  r="5"
                  fill={color}
                />
              )}
            </g>
          )
        })}
      </svg>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
        {clientIds.map((cid, idx) => (
          <div key={cid} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: COLORS[idx % COLORS.length] }} />
            <span>{cid}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
