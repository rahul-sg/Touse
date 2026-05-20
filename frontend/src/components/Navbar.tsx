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
      <NavLink to={isLoggedIn ? '/dashboard' : '/'} className={styles.brand}>
        Touse
      </NavLink>
      <div className={styles.links}>
        {isLoggedIn && (
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? styles.active : '')}>
            Dashboard
          </NavLink>
        )}
        <NavLink to="/map" className={({ isActive }) => (isActive ? styles.active : '')}>
          Map
        </NavLink>
        <NavLink to="/about" className={({ isActive }) => (isActive ? styles.active : '')}>
          About
        </NavLink>
        {isLoggedIn ? (
          <button className={styles.signOutBtn} onClick={handleLogout}>
            {user?.first_name ? `Sign out` : 'Sign out'}
          </button>
        ) : (
          <NavLink to="/login" className={styles.signInBtn}>
            Sign in
          </NavLink>
        )}
      </div>
    </nav>
  )
}
