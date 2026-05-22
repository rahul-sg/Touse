import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Onboarding from './pages/Onboarding'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import MapView from './pages/MapView'
import Forecast from './pages/Forecast'
import About from './pages/About'
import Scenarios from './pages/Scenarios'
import ScenarioDetail from './pages/ScenarioDetail'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/forecast/:zip" element={<Forecast />} />
            <Route path="/about" element={<About />} />
            <Route path="/scenarios" element={<Scenarios />} />
            <Route path="/scenarios/:publicId" element={<ScenarioDetail />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
