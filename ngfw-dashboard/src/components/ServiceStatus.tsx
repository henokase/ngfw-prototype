interface ServiceStatusProps {
  name: string
  status: 'active' | 'inactive' | 'warning'
  port?: string
}

const serviceDisplayNames: Record<string, string> = {
  'suricata': 'Suricata IDS/IPS',
  'ngfw-control': 'NGFW Control API',
  'ngfw-ml': 'ML Inference Service',
  'ngfw-flowmeter': 'Flow Meter',
  'suri-clam': 'Suricata-ClamAV',
  'clamav-daemon': 'ClamAV Daemon',
}

const ServiceStatus: React.FC<ServiceStatusProps> = ({ name, status, port }) => {
  const statusClasses = {
    active: 'status-dot active',
    inactive: 'status-dot inactive',
    warning: 'status-dot warning',
  }

  const borderClasses = {
    active: 'border-success/20',
    inactive: 'border-danger/20',
    warning: 'border-warning/20',
  }

  return (
    <div className={`card p-4 flex items-center justify-between ${borderClasses[status]}`}>
      <div className="flex items-center gap-3">
        <span className={statusClasses[status]} />
        <div>
          <p className="text-sm font-medium text-primary">{serviceDisplayNames[name] || name}</p>
          <p className="text-xs text-muted">{name}.service</p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-xs font-mono ${status === 'active' ? 'text-success' : status === 'warning' ? 'text-warning' : 'text-danger'}`}>
          {status.toUpperCase()}
        </p>
        {port && <p className="text-xs text-gray-600 font-mono">:{port}</p>}
      </div>
    </div>
  )
}

export default ServiceStatus