import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './Navbar.module.css'

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <nav className={styles.nav}>
      {/* Logo always returns to the landing page. */}
      <NavLink to="/" className={styles.brand}>
        Touse
      </NavLink>
      <div className={styles.links}>
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
