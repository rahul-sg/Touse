import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface Props {
  className?: string
  children: ReactNode
}

/**
 * "Get started" / "Create account" CTA.
 *
 * If the user is already signed in, intercepts the click and asks whether
 * they want to sign out and start a new account (the alternative would be
 * to silently send a signed-in user to the onboarding form, which is
 * confusing because the navbar still shows their old session).
 */
export default function NewAccountCta({ className, children }: Props) {
  const { isLoggedIn, user, logout } = useAuth()
  const navigate = useNavigate()
  const [confirmOpen, setConfirmOpen] = useState(false)

  function handleClick(e: React.MouseEvent) {
    e.preventDefault()
    if (isLoggedIn) {
      setConfirmOpen(true)
    } else {
      navigate('/onboarding')
    }
  }

  function confirmSwitch() {
    logout()
    setConfirmOpen(false)
    navigate('/onboarding')
  }

  return (
    <>
      <a href="/onboarding" className={className} onClick={handleClick}>
        {children}
      </a>

      {confirmOpen && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setConfirmOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: '1rem',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff', borderRadius: 8, padding: '1.75rem',
              maxWidth: 420, width: '100%', boxShadow: '0 12px 32px rgba(0,0,0,0.25)',
              fontFamily: 'inherit',
            }}
          >
            <h2 style={{ margin: 0, color: '#1C3A2F', fontSize: '1.25rem' }}>
              Sign out and create a new account?
            </h2>
            <p style={{ color: '#555', marginTop: '0.75rem', fontSize: '0.95rem', lineHeight: 1.5 }}>
              You're currently signed in as <strong>{user?.first_name ?? user?.username}</strong>.
              Continuing will sign you out and start fresh.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                style={{
                  padding: '0.55rem 1rem', borderRadius: 4, border: '1px solid #ccc',
                  background: 'transparent', cursor: 'pointer', fontWeight: 500,
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmSwitch}
                style={{
                  padding: '0.55rem 1rem', borderRadius: 4, border: 'none',
                  background: '#1C3A2F', color: '#fff', cursor: 'pointer', fontWeight: 600,
                }}
              >
                Sign out and continue
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
