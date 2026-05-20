import { NavLink } from 'react-router-dom'
import styles from './Navbar.module.css'

export default function Navbar() {
  return (
    <nav className={styles.nav}>
      <NavLink to="/" className={styles.brand}>Touse</NavLink>
      <div className={styles.links}>
        <NavLink to="/map" className={({ isActive }) => isActive ? styles.active : ''}>Map</NavLink>
        <NavLink to="/about" className={({ isActive }) => isActive ? styles.active : ''}>About</NavLink>
      </div>
    </nav>
  )
}
