import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Shield, AlertCircle, ArrowRight, Eye, EyeOff } from 'lucide-react'

const Login: React.FC = () => {
  const { isAuthenticated, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    await new Promise(resolve => setTimeout(resolve, 600))

    const success = login(email, password)
    if (!success) {
      setError('Invalid credentials. Please try again.')
    }
    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-inset">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-cyan/5 blur-[100px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-danger/5 blur-[120px]" />
        </div>
        
        <svg className="absolute inset-0 w-full h-full opacity-[0.015]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-cyan" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="bg-card/80 backdrop-blur-xl border border-subtle/50 rounded-2xl p-8 sm:p-10 shadow-2xl shadow-black/50">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-cyan/5 border border-cyan/10 mb-4">
              <Shield className="w-7 h-7 text-cyan" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight">
              NGFW <span className="text-cyan">Dashboard</span>
            </h1>
            <p className="text-muted mt-2 text-sm">Secure access portal</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-secondary ml-1">
                Email / Username
              </label>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin"
                className="w-full px-4 py-3.5 bg-card border border-subtle rounded-xl text-primary placeholder-muted focus:outline-none focus:border-cyan/25 focus:ring-1 focus:ring-cyan/10 transition-all duration-200"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-secondary ml-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3.5 pr-12 bg-card border border-subtle rounded-xl text-primary placeholder-muted focus:outline-none focus:border-cyan/25 focus:ring-1 focus:ring-cyan/10 transition-all duration-200"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-secondary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-danger/10 border border-danger/10 rounded-lg">
                <AlertCircle className="w-4 h-4 text-danger flex-shrink-0" />
                <p className="text-sm text-danger">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-cyan to-cyan text-[var(--color-bg-inverse)] font-semibold rounded-xl hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-cyan/25 focus:ring-offset-2 focus:ring-offset-[var(--color-bg-deep)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-[var(--color-text-muted)] border-t-[var(--color-text-primary)] rounded-full animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-subtle">
            <p className="text-xs text-tertiary text-center">
              Demo credentials: <span className="text-secondary">admin</span> / <span className="text-secondary">Pass123!</span>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-tertiary mt-6">
          NGFW Prototype v1.0 • Protected Access
        </p>
      </div>
    </div>
  )
}

export default Login