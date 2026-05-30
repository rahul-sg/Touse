import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './Navbar.module.css'

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  // Close the mobile menu whenever the user navigates.
  useEffect(() => { setOpen(false) }, [location.pathname])

  // Lock body scroll while the mobile menu drawer is open.
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }
  }, [open])

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <nav className={styles.nav}>
      <NavLink to="/" className={styles.brand}>Touse</NavLink>

      <button
        className={styles.hamburger}
        aria-label="Toggle menu"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        <span /><span /><span />
      </button>

      <div className={`${styles.links} ${open ? styles.linksOpen : ''}`}>
        {isLoggedIn && (
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? styles.active : '')}>
            Dashboard
          </NavLink>
        )}
        {isLoggedIn && (
          <NavLink to="/map" className={({ isActive }) => (isActive ? styles.active : '')}>
            Map
          </NavLink>
        )}
        <NavLink to="/about" className={({ isActive }) => (isActive ? styles.active : '')}>
          About
        </NavLink>
        {isLoggedIn ? (
          <>
            {user?.first_name && (
              <NavLink to="/profile" className={styles.userName}>
                Hi, {user.first_name}
              </NavLink>
            )}
            <button className={styles.signOutBtn} onClick={handleLogout}>
              Sign out
            </button>
          </>
        ) : (
          <NavLink to="/login" className={styles.signInBtn}>
            Sign in
          </NavLink>
        )}
      </div>
    </nav>
  )
}
