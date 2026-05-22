import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate, useLocation, Location } from 'react-router-dom'

interface AuthContextType {
  isAuthenticated: boolean
  login: (email: string, password: string) => boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

const CREDENTIALS = {
  email: 'admin',
  password: 'Pass123!'
}

const AuthInner: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem('ngfw_auth') === 'true'
  })
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    localStorage.setItem('ngfw_auth', String(isAuthenticated))
  }, [isAuthenticated])

  const login = (email: string, password: string): boolean => {
    if (email === CREDENTIALS.email && password === CREDENTIALS.password) {
      setIsAuthenticated(true)
      const from = (location.state as Location)?.pathname || '/'
      navigate(from, { replace: true })
      return true
    }
    return false
  }

  const logout = () => {
    setIsAuthenticated(false)
    navigate('/login', { replace: true })
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <AuthInner>{children}</AuthInner>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}