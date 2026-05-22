import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardHome from './components/DashboardHome'
import FirewallManagement from './components/FirewallManagement'
import AttackLogs from './components/AttackLogs'
import MalwareDetection from './components/MalwareDetection'
import MLDetection from './components/MLDetection'
import ServiceControl from './components/ServiceControl'
import NetworkOverview from './components/NetworkOverview'
import Login from './pages/Login'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<DashboardHome />} />
            <Route path="firewall" element={<FirewallManagement />} />
            <Route path="logs" element={<AttackLogs />} />
            <Route path="malware" element={<MalwareDetection />} />
            <Route path="ml" element={<MLDetection />} />
            <Route path="services" element={<ServiceControl />} />
            <Route path="network" element={<NetworkOverview />} />
          </Route>
        </Routes>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App