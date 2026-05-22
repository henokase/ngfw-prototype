import { useState, useEffect, useCallback } from 'react'
import { Server, Play, Square, RotateCw, Zap } from 'lucide-react'
import { getServices, controlService, type Service } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'

const serviceDefinitions: { name: string; displayName: string; port?: string }[] = [
  { name: 'suricata', displayName: 'Suricata IDS/IPS' },
  { name: 'ngfw-control', displayName: 'NGFW Control API', port: '5001' },
  { name: 'ngfw-ml', displayName: 'ML Inference Service', port: '5003' },
  { name: 'ngfw-flowmeter', displayName: 'Flow Meter' },
  { name: 'suri-clam', displayName: 'Suricata-ClamAV' },
  { name: 'clamav-daemon', displayName: 'ClamAV Daemon' },
]

const ServiceControl: React.FC = () => {
  const [serviceStates, setServiceStates] = useState<Record<string, 'active' | 'inactive' | 'loading'>>({
    suricata: 'inactive',
    'ngfw-control': 'inactive',
    'ngfw-ml': 'inactive',
    'ngfw-flowmeter': 'inactive',
    'suri-clam': 'inactive',
    'clamav-daemon': 'inactive',
  })
  const [actionService, setActionService] = useState<string | null>(null)

  const handleSSE = useCallback((data: SSEMessage) => {
    if (data.services) {
      const newStates: Record<string, Service['status']> = {}
      for (const s of data.services) {
        newStates[s.name] = s.status as Service['status']
      }
      setServiceStates(prev => ({ ...prev, ...newStates }))
    }
  }, [])

  useSSE('system_update', handleSSE, true)

  const fetchServices = async () => {
    try {
      const data = await getServices()
      if (data.success && data.services) {
        const newStates: Record<string, Service['status']> = {}
        for (const svc of data.services) {
          newStates[svc.name] = svc.status
        }
        setServiceStates(prev => ({ ...prev, ...newStates }))
      }
    } catch (err) {
      console.error('Failed to fetch services:', err)
    }
  }

  useEffect(() => {
    fetchServices()
    const interval = setInterval(fetchServices, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (serviceName: string, action: 'start' | 'stop' | 'restart') => {
    if (serviceName === 'ngfw-control' && (action === 'stop' || action === 'restart')) {
      alert('Cannot stop/restart ngfw-control service via dashboard.')
      return
    }

    setActionService(serviceName)

    setServiceStates((prev) => ({
      ...prev,
      [serviceName]: action === 'stop' ? 'inactive' : 'loading',
    }))

    try {
      await controlService(serviceName, action)
      setTimeout(async () => {
        await fetchServices()
        setActionService(null)
      }, 2000)
    } catch (err) {
      console.error('Service action failed:', err)
      setServiceStates((prev) => ({
        ...prev,
        [serviceName]: prev[serviceName] || 'inactive',
      }))
      setActionService(null)
    }
  }

  const getStatusColor = (status: 'active' | 'inactive' | 'loading') => {
    if (status === 'active') return 'text-success'
    if (status === 'loading') return 'text-warning'
    return 'text-danger'
  }

  const activeCount = Object.values(serviceStates).filter(s => s === 'active').length

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="card p-4 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 md:mb-6">
          <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary flex items-center gap-2">
            <Server className="w-5 h-5 text-cyan" />
            Service Management
          </h3>
          <div className="flex items-center gap-2">
            <span className={`status-dot ${activeCount > 0 ? 'active' : ''}`} />
            <span className="text-sm text-muted">
              {activeCount}/{serviceDefinitions.length} active
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
          {serviceDefinitions.map((service) => {
            const currentStatus = serviceStates[service.name] || 'inactive'
            const isLoading = actionService === service.name

            return (
              <div
                key={service.name}
                className="flex flex-col p-4 md:p-5 bg-deep rounded-lg border border-subtle"
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-lg ${
                      currentStatus === 'active' 
                        ? 'bg-success/10' 
                        : currentStatus === 'loading'
                        ? 'bg-warning/10'
                        : 'bg-danger/10'
                    }`}>
                      <Server className={`w-5 h-5 ${
                        currentStatus === 'active' 
                          ? 'text-success' 
                          : currentStatus === 'loading'
                          ? 'text-warning'
                          : 'text-danger'
                      }`} />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-primary leading-tight">{service.displayName}</p>
                      <p className="text-xs text-muted mt-0.5">{service.name}.service{service.port ? ` :${service.port}` : ''}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-mono font-medium px-2 py-1 rounded ${getStatusColor(currentStatus)} bg-current/10`}>
                    {isLoading ? 'LOADING' : currentStatus.toUpperCase()}
                  </span>
                </div>

                <div className="flex items-center gap-2 mt-auto">
                  <button
                    onClick={() => handleAction(service.name, 'start')}
                    disabled={actionService !== null || currentStatus === 'active'}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-success/10 text-success hover:bg-success/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                    title="Start"
                  >
                    <Play className="w-4 h-4" />
                    <span>Start</span>
                  </button>
                  <button
                    onClick={() => handleAction(service.name, 'stop')}
                    disabled={actionService !== null || currentStatus === 'inactive' || service.name === 'ngfw-control'}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-danger/10 text-danger hover:bg-danger/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                    title="Stop"
                  >
                    <Square className="w-4 h-4" />
                    <span>Stop</span>
                  </button>
                  <button
                    onClick={() => handleAction(service.name, 'restart')}
                    disabled={actionService !== null || currentStatus === 'inactive' || service.name === 'ngfw-control'}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-warning/10 text-warning hover:bg-warning/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                    title="Restart"
                  >
                    <RotateCw className="w-4 h-4" />
                    <span>Restart</span>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="card p-4 md:p-6">
        <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-cyan" />
          Quick Actions
        </h3>
        <div className="flex flex-col sm:flex-row flex-wrap gap-3">
          <button
            onClick={() => {
              serviceDefinitions.forEach((s) => {
                if (s.name !== 'ngfw-control' && serviceStates[s.name] !== 'active') {
                  handleAction(s.name, 'start')
                }
              })
            }}
            className="btn-primary min-h-[44px]"
          >
            <Play className="w-4 h-4 inline mr-1" />
            Start All
          </button>
          <button
            onClick={() => {
              serviceDefinitions.forEach((s) => {
                if (s.name !== 'ngfw-control' && serviceStates[s.name] === 'active') {
                  handleAction(s.name, 'stop')
                }
              })
            }}
            className="btn-danger min-h-[44px]"
          >
            <Square className="w-4 h-4 inline mr-1" />
            Stop All
          </button>
          <button
            onClick={() => {
              serviceDefinitions.forEach((s) => {
                if (s.name !== 'ngfw-control' && serviceStates[s.name] === 'active') {
                  handleAction(s.name, 'restart')
                }
              })
            }}
            className="btn-secondary min-h-[44px]"
          >
            <RotateCw className="w-4 h-4 inline mr-1" />
            Restart All
          </button>
        </div>
      </div>
    </div>
  )
}

export default ServiceControl