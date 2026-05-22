import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Shield, 
  FileText, 
  Bug, 
  Brain, 
  Network,
  Hexagon,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import ConfirmModal from './ConfirmModal'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/firewall', icon: Shield, label: 'Firewall' },
  { to: '/logs', icon: FileText, label: 'Detection Logs' },
  { to: '/malware', icon: Bug, label: 'Malware' },
  { to: '/ml', icon: Brain, label: 'ML Detection' },
  { to: '/network', icon: Network, label: 'Network' },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { logout } = useAuth()
  const [showSignOutModal, setShowSignOutModal] = useState(false)

  return (
    <>
      <ConfirmModal
        isOpen={showSignOutModal}
        onClose={() => setShowSignOutModal(false)}
        onConfirm={logout}
        title="Sign Out"
        message="Are you sure you want to sign out? You will need to re-enter your credentials to access the dashboard."
        confirmText="Sign Out"
        confirmVariant="danger"
      />

      <aside className={`
        fixed left-0 top-0 h-screen w-64 bg-card border-r border-subtle
        flex flex-col z-50 transition-transform duration-300 ease-in-out
        lg:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="p-6 border-b border-subtle">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Hexagon className="w-10 h-10 text-cyan" strokeWidth={1.5} />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-3 h-3 bg-cyan rounded-sm animate-pulse" />
              </div>
            </div>
            <div>
              <h1 className="font-[family-name:var(--font-display)] text-lg font-bold text-primary tracking-wide">
                NGFW
              </h1>
              <p className="text-[10px] text-cyan-dim uppercase tracking-[0.2em]">
                Operations Center
              </p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group relative overflow-hidden ${
                  isActive
                    ? 'bg-cyan/10 text-cyan border border-cyan/20'
                    : 'text-secondary hover:bg-card-hover hover:text-primary'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan shadow-[0_0_10px_var(--color-cyan)]" />
                  )}
                  <item.icon className={`w-5 h-5 ${isActive ? 'text-cyan' : 'text-muted group-hover:text-cyan'}`} />
                  <span className="text-sm font-medium">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-subtle">
          <button
            onClick={() => setShowSignOutModal(true)}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg text-sm text-secondary hover:text-danger hover:bg-danger/10 transition-all duration-200"
          >
            <LogOut className="w-4 h-4" />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
