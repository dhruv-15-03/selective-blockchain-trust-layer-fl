import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { motion } from 'framer-motion'
import Scene3D from '../components/Scene3D'

export default function Home() {
  const heroRef = useRef()
  const titleRef = useRef()
  const leadRef = useRef()
  const cardsRef = useRef([])

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(titleRef.current, { opacity: 0, y: 60, duration: 1, ease: 'power3.out' })
      gsap.from(leadRef.current, { opacity: 0, y: 40, duration: 0.9, delay: 0.2, ease: 'power3.out' })
      gsap.from(cardsRef.current, {
        opacity: 0,
        y: 50,
        duration: 0.8,
        stagger: 0.15,
        delay: 0.4,
        ease: 'power3.out',
      })
    }, heroRef)
    return () => ctx.revert()
  }, [])

  return (
    <div ref={heroRef} className="page" style={{ position: 'relative', overflow: 'hidden' }}>
      <Scene3D />
      <div style={{ position: 'relative', zIndex: 1, paddingTop: '4rem' }}>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          style={{ textAlign: 'center', maxWidth: 800, margin: '0 auto' }}
        >
          <h1
            ref={titleRef}
            style={{
              fontSize: 'clamp(2.5rem, 6vw, 4rem)',
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              marginBottom: '1rem',
            }}
          >
            TrustScore for Upwork Clients
          </h1>
          <p
            ref={leadRef}
            style={{ fontSize: '1.2rem', color: 'var(--muted)', lineHeight: 1.6 }}
          >
            ML-based malicious participant detection + on-chain TrustScore + blacklist.
            Live demo UI to show how trust changes across rounds.
          </p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginTop: '2rem' }}
          >
            <Link to="/upwork/create" className="btn btn-primary">
              Start Demo
            </Link>
            <Link to="/dashboard" className="btn btn-secondary">
              Dashboard
            </Link>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="btn btn-secondary">
              API Docs
            </a>
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9 }}
            style={{ marginTop: '2rem', display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}
          >
            <span className="badge badge-low">FastAPI</span>
            <span className="badge badge-low">Ganache</span>
            <span className="badge" style={{ color: 'var(--accent-secondary)', borderColor: 'var(--accent-secondary)' }}>
              Demo: http://127.0.0.1:8000
            </span>
          </motion.div>
        </motion.div>

        <div className="grid-2" style={{ marginTop: '4rem' }}>
          {[
            {
              title: 'What you can show to judges',
              items: [
                'Honest participants keep trust high',
                'Malicious participant gets flagged by ML gate',
                'Server calls smart contract to penalize & blacklist',
                'Dashboard shows trust evolution and risk status',
              ],
            },
            {
              title: 'How to run (quick)',
              items: [
                'Step 1: Start backend server',
                'Step 2: Start Ganache',
                'Step 3: Run clients (client1, client2, client3, malicious_client)',
                'Step 4: Click Aggregate & View Results',
              ],
            },
          ].map((card, i) => (
            <motion.div
              key={card.title}
              ref={(el) => (cardsRef.current[i] = el)}
              className="card"
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
            >
              <h2 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>{card.title}</h2>
              <ul style={{ color: 'var(--muted)', fontSize: '0.95rem', lineHeight: 1.8, paddingLeft: '1.25rem' }}>
                {card.items.map((item, j) => (
                  <li key={j}>{item}</li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        <motion.div
          ref={(el) => (cardsRef.current[2] = el)}
          className="card"
          style={{ marginTop: '1.5rem' }}
          whileHover={{ y: -4 }}
        >
          <h2 style={{ marginBottom: '0.5rem' }}>Important</h2>
          <p style={{ color: 'var(--muted)' }}>
            Malicious trust drop is easiest when Ganache is fresh (or contract redeployed).
            If malicious client is already blacklisted, just restart Ganache/contract for a clean demo.
          </p>
        </motion.div>
      </div>
    </div>
  )
}
