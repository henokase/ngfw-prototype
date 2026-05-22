import { useLocation } from 'react-router-dom'
import { Clock, User, Menu } from 'lucide-react'
import ThemeToggle from './ThemeToggle'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard Overview',
  '/firewall': 'Firewall Management',
  '/logs': 'Detection Logs',
  '/malware': 'Malware Detection',
  '/ml': 'ML Anomaly Detection',
  '/services': 'Service Control',
  '/network': 'Network Overview',
}

interface HeaderProps {
  onMenuClick: () => void
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Dashboard'
  return (
    <header className="h-16 bg-card border-b border-subtle px-4 md:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button 
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-2 text-secondary hover:text-cyan transition-colors"
        >
          <Menu className="w-6 h-6" />
        </button>
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg md:text-xl font-semibold text-primary">
            {title}
          </h2>
          <p className="text-xs text-muted mt-0.5 hidden sm:block">
            NGFW Prototype v1.0 • Operations Monitoring
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 md:gap-6">
        <ThemeToggle />

        <div className="hidden sm:flex items-center gap-2 text-xs text-muted">
          <Clock className="w-4 h-4" />
          <span className="font-mono hidden md:inline">
            {new Date().toLocaleDateString('en-US', { 
              weekday: 'short', 
              month: 'short', 
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>

        <div className="flex items-center gap-2 md:gap-3 pl-2 md:pl-4 border-l border-subtle">
          <div className="w-8 h-8 rounded-full bg-cyan/10 border border-cyan/20 flex items-center justify-center">
            <User className="w-4 h-4 text-cyan" />
          </div>
          <div className="text-sm hidden sm:block">
            <p className="text-primary font-medium">Admin</p>
            <p className="text-xs text-muted">Operations</p>
          </div>
        </div>

      </div>
    </header>
  )
}

export default Header