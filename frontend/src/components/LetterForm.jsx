import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'

export default function LetterForm({ children, title, isOpen = true }) {
  const windowRef = useRef()
  const letterRef = useRef()
  const frameRef = useRef()

  useEffect(() => {
    if (!windowRef.current || !letterRef.current) return
    if (isOpen) {
      gsap.to(letterRef.current, {
        y: 0,
        rotateX: 0,
        opacity: 1,
        duration: 1,
        ease: 'power3.out',
        overwrite: true,
      })
      gsap.to(frameRef.current, {
        scale: 1,
        opacity: 1,
        duration: 0.8,
        ease: 'back.out(1.2)',
      })
    } else {
      gsap.to(letterRef.current, {
        y: -80,
        rotateX: -15,
        opacity: 0.8,
        duration: 0.6,
        ease: 'power2.in',
      })
    }
  }, [isOpen])

  return (
    <div
      ref={windowRef}
      style={{
        perspective: '1200px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        minHeight: '60vh',
        padding: '2rem',
      }}
    >
      {/* 3D Window Frame */}
      <div
        ref={frameRef}
        style={{
          position: 'relative',
          width: 'min(420px, 95vw)',
          padding: '20px',
          background: 'linear-gradient(145deg, #1e293b 0%, #0f172a 100%)',
          borderRadius: '8px',
          boxShadow: `
            inset 0 0 0 3px rgba(99, 102, 241, 0.3),
            inset 0 0 40px rgba(0,0,0,0.5),
            0 25px 50px rgba(0,0,0,0.5),
            0 0 0 1px rgba(148,163,184,0.2)
          `,
          transformStyle: 'preserve-3d',
        }}
      >
        {/* Window cross / frame lines */}
        <div
          style={{
            position: 'absolute',
            inset: 20,
            border: '2px solid rgba(99, 102, 241, 0.4)',
            borderRadius: 4,
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 20,
            bottom: 20,
            width: 2,
            background: 'rgba(99, 102, 241, 0.4)',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
          }}
        />
        {/* Letter slides out from here */}
        <div
          ref={letterRef}
          style={{
            position: 'relative',
            transformStyle: 'preserve-3d',
            transform: 'translateY(-60px) rotateX(-12deg)',
            opacity: 0.9,
            background: 'linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)',
            borderRadius: 4,
            padding: '2rem 1.75rem',
            boxShadow: `
              0 4px 6px rgba(0,0,0,0.1),
              0 1px 3px rgba(0,0,0,0.08),
              inset 0 1px 0 rgba(255,255,255,0.9)
            `,
            border: '1px solid rgba(148,163,184,0.3)',
          }}
        >
          {/* Letter fold/crease line at top */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: '10%',
              right: '10%',
              height: 3,
              background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.2), transparent)',
              borderRadius: 2,
            }}
          />
          <h2
            style={{
              margin: '0 0 1.5rem',
              fontSize: '1.5rem',
              fontWeight: 700,
              color: '#0f172a',
              textAlign: 'center',
              letterSpacing: '-0.02em',
            }}
          >
            {title}
          </h2>
          {children}
        </div>
      </div>
    </div>
  )
}
