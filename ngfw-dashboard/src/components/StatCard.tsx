import { ReactNode } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  icon: ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  variant?: 'default' | 'danger' | 'warning' | 'success'
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  icon, 
  trend = 'neutral',
  trendValue,
  variant = 'default'
}) => {
  const variantClasses = {
    default: 'text-cyan border-cyan/20',
    danger: 'text-danger border-danger/20',
    warning: 'text-warning border-warning/20',
    success: 'text-success border-success/20',
  }

  const iconBgClasses = {
    default: 'bg-cyan/10',
    danger: 'bg-danger/10',
    warning: 'bg-warning/10',
    success: 'bg-success/10',
  }

  return (
    <div className="card p-5 relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-cyan/5 to-transparent rounded-full -translate-y-1/2 translate-x-1/2" />
      
      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-xs text-muted uppercase tracking-wider mb-1">{title}</p>
          <p className={`text-3xl font-[family-name:var(--font-display)] font-bold ${variantClasses[variant].split(' ')[0]}`}>
            {value}
          </p>
          {trendValue && (
            <div className={`flex items-center gap-1 mt-2 text-xs ${
              trend === 'up' ? 'text-success' : trend === 'down' ? 'text-danger' : 'text-muted'
            }`}>
              {trend === 'up' && <TrendingUp className="w-3 h-3" />}
              {trend === 'down' && <TrendingDown className="w-3 h-3" />}
              <span>{trendValue}</span>
            </div>
          )}
        </div>
        
        <div className={`p-3 rounded-lg ${iconBgClasses[variant]}`}>
          {icon}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  )
}

export default StatCard