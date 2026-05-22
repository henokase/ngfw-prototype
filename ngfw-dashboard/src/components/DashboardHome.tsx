import { useState, useEffect, useCallback } from 'react'
import { Shield, AlertTriangle, Skull, Activity, Server, Network, Power, PowerOff } from 'lucide-react'
import StatCard from './StatCard'
import ServiceStatus from './ServiceStatus'
import ConfirmModal from './ConfirmModal'
import { getHealth, getServices, getSystemStats, getNetworkStats, getMalwareAlerts, controlService, type Service, type SystemStats, type NetworkStats } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'

const DashboardHome: React.FC = () => {
  const [stats, setStats] = useState({
    blockedIPs: 0,
    eventsToday: 0,
    activeThreats: 0,
    malwareDetected: 0,
    mlAnomalies: 0,
  })

  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [services, setServices] = useState<Service[]>([])
  const [networkStats, setNetworkStats] = useState<NetworkStats | null>(null)
  const [toggling, setToggling] = useState(false)
  const [showFirewallOffModal, setShowFirewallOffModal] = useState(false)
  const [loading, setLoading] = useState(true)

  const suricataIpsService = services.find(s => s.name === 'suricata-ips')
  const firewallActive = suricataIpsService?.status === 'active'

  const handleFirewallToggleRequest = () => {
    if (firewallActive) {
      setShowFirewallOffModal(true)
    } else {
      handleFirewallToggle()
    }
  }

  const handleFirewallToggle = async () => {
    if (toggling) return
    setShowFirewallOffModal(false)
    setToggling(true)
    try {
      const action = firewallActive ? 'stop' : 'start'
      await controlService('suricata-ips', action as 'start' | 'stop')
      await controlService('suri-clam', action as 'start' | 'stop')
      await controlService('ngfw-ml', action as 'start' | 'stop')
      setTimeout(async () => {
        const data = await getServices()
        if (data.success) setServices(data.services)
        setToggling(false)
      }, 3000)
    } catch (err) {
      console.error('Failed to toggle firewall:', err)
      setToggling(false)
    }
  }

  const serviceDisplayNames: Record<string, string> = {
    'suricata-ips': 'DPI Engine',
    'ngfw-control': 'Decision Engine',
    'ngfw-ml': 'ML Inference Service',
    'ngfw-flowmeter': 'Flow Meter',
    'suri-clam': 'Suricata-ClamAV',
    'clamav-daemon': 'ClamAV Daemon',
  }

  const handleSSE = useCallback((data: SSEMessage) => {
    if (data.services) {
      setServices(data.services.map(s => ({
        name: s.name,
        displayName: serviceDisplayNames[s.name] || s.name,
        port: s.name === 'ngfw-control' ? 5001 : s.name === 'ngfw-ml' ? 5003 : null,
        status: s.status as 'active' | 'inactive',
      })))
    }
    if (data.stats) {
      setSystemStats(prev => prev ? {
        ...prev,
        cpu_load: data.stats!.cpu_load,
        memory_percent: data.stats!.memory_percent,
        events_today: data.stats!.events_today,
        active_threats: data.stats!.active_threats,
      } : null)
      setStats(prev => ({
        blockedIPs: data.blocks?.length || 0,
        eventsToday: data.stats!.events_today,
        activeThreats: data.stats!.active_threats,
        malwareDetected: data.malwareDetected || prev.malwareDetected,
        mlAnomalies: prev.mlAnomalies,
      }))
    }
    if (data.packets_in !== undefined) {
      setNetworkStats(prev => prev ? {
        ...prev,
        packets_in: data.packets_in!,
        packets_out: data.packets_out!,
        bytes_in: data.bytes_in!,
        bytes_out: data.bytes_out!,
      } : null)
    }
    if (data.ml_prediction) {
      setStats(prev => ({ ...prev, mlAnomalies: prev.mlAnomalies + 1 }))
    }
  }, [])

  useSSE('system_update', handleSSE, true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthData, servicesData, sysStats, netStats, malwareData] = await Promise.all([
          getHealth(),
          getServices(),
          getSystemStats(),
          getNetworkStats(),
          getMalwareAlerts(100),
        ])

        const malwareCount = malwareData.success 
          ? malwareData.alerts.filter((a: any) => a.action === 'blocked').length 
          : 0

        setStats(prev => ({
          blockedIPs: healthData.total_blocked_ips,
          eventsToday: healthData.total_events_today,
          activeThreats: healthData.active_threats,
          malwareDetected: malwareCount,
          mlAnomalies: prev.mlAnomalies,
        }))

        if (servicesData.success) {
          setServices(servicesData.services)
        }

        if (sysStats.success) {
          setSystemStats(sysStats.stats)
        }

        if (netStats.success) {
          setNetworkStats(netStats.stats)
        }
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const getInterfaceInfo = (name: string) => {
    if (!networkStats?.interfaces) return null
    return networkStats.interfaces.find(i => i.name === name)
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    return `${days}d ${hours}h`
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <ConfirmModal
        isOpen={showFirewallOffModal}
        onClose={() => setShowFirewallOffModal(false)}
        onConfirm={handleFirewallToggle}
        title="Disable Firewall Protection"
        message="Are you sure you want to disable the firewall? Your system will be vulnerable to attacks until re-enabled."
        confirmText="Disable"
        confirmVariant="danger"
        loading={toggling}
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4">
        <StatCard
          title="Blocked IPs"
          value={stats.blockedIPs}
          icon={<Shield className="w-5 h-5 text-cyan" />}
          variant="warning"
        />
        <StatCard
          title="Events Today"
          value={stats.eventsToday}
          icon={<Activity className="w-5 h-5 text-cyan" />}
        />
        <StatCard
          title="Active Threats"
          value={stats.activeThreats}
          icon={<AlertTriangle className="w-5 h-5 text-danger" />}
          variant="danger"
        />
        <StatCard
          title="Malware Detected"
          value={stats.malwareDetected}
          icon={<Skull className="w-5 h-5 text-warning" />}
          variant="warning"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <div className="card p-4 md:p-6">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan" />
              <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary">
                Service Status
              </h3>
            </div>
            {!loading && (
              <button
                onClick={handleFirewallToggleRequest}
                disabled={toggling}
                className={`p-2 rounded-lg transition-all ${
                  firewallActive
                    ? 'bg-success/10 hover:bg-success/20'
                    : 'bg-danger/10 hover:bg-danger/20'
                } disabled:opacity-50`}
                title={firewallActive ? 'Disable Firewall' : 'Enable Firewall'}
              >
                {toggling ? (
                  <Activity className="w-5 h-5 text-secondary animate-spin" />
                ) : firewallActive ? (
                  <Power className="w-5 h-5 text-success" />
                ) : (
                  <PowerOff className="w-5 h-5 text-danger" />
                )}
              </button>
            )}
          </div>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="relative overflow-hidden rounded-lg p-4 bg-deep/80 border border-subtle">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#1a1a2e] to-[#0a0a0f] flex items-center justify-center">
                      <div className="w-4 h-4 rounded-full bg-cyan/20 shimmer-glow" />
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-32 shimmer-bg rounded shimmer-animation" />
                      <div className="h-3 w-20 shimmer-bg rounded shimmer-animation" />
                    </div>
                    <div className="w-16 h-6 rounded-full bg-gradient-to-r from-[#00ff881a] via-[#00ff8833] to-[#00ff881a] shimmer-animation" />
                  </div>
                </div>
              ))}
            </div>
          ) : !firewallActive ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <PowerOff className="w-12 h-12 text-danger mb-3" />
              <p className="text-lg font-medium text-danger">Firewall Deactivated</p>
              <p className="text-sm text-muted mt-1">Click the power button to enable protection</p>
            </div>
          ) : (
            <div className="space-y-3">
              {services.length > 0 ? services.map((service) => {
                const displayName = service.displayName || service.name
                return (
                  <div key={service.name} className={service.name === 'suri-clam' ? 'hidden' : ''}>
                    <ServiceStatus name={displayName} status={service.status} port={service.port?.toString()} />
                  </div>
                )
              }) : (
                <div className="text-muted text-sm">Loading services...</div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="card p-4 md:p-6">
            <div className="flex items-center gap-2 mb-4">
              <Network className="w-5 h-5 text-cyan" />
              <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary">
                Network Interfaces
              </h3>
            </div>
            <div className="space-y-3 md:space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 md:p-4 bg-deep rounded-lg border border-subtle">
                <div>
                  <p className="text-sm font-medium text-primary">enp0s3 (External)</p>
                  <p className="text-xs text-muted">Connected to host/internet</p>
                </div>
                <div className="text-left sm:text-right">
                  {networkStats?.interfaces ? (
                    <>
                      {(() => {
                        const iface = getInterfaceInfo('enp0s3')
                        return iface ? (
                          <>
                            <p className="text-sm font-mono text-success">{iface.ip || 'N/A'}</p>
                            <p className={`text-xs ${iface.status === 'up' ? 'text-success' : 'text-danger'}`}>
                              ● {iface.status || 'unknown'}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-sm font-mono text-success">192.168.1.70/24</p>
                            <p className="text-xs text-success">● Active</p>
                          </>
                        )
                      })()}
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-mono text-success">192.168.1.70/24</p>
                      <p className="text-xs text-success">● Active</p>
                    </>
                  )}
                </div>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 md:p-4 bg-deep rounded-lg border border-subtle">
                <div>
                  <p className="text-sm font-medium text-primary">enp0s8 (Internal)</p>
                  <p className="text-xs text-muted">Connected to test server</p>
                </div>
                <div className="text-left sm:text-right">
                  {networkStats?.interfaces ? (
                    <>
                      {(() => {
                        const iface = getInterfaceInfo('enp0s8')
                        return iface ? (
                          <>
                            <p className="text-sm font-mono text-success">{iface.ip || 'N/A'}</p>
                            <p className={`text-xs ${iface.status === 'up' ? 'text-success' : 'text-danger'}`}>
                              ● {iface.status || 'unknown'}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-sm font-mono text-success">10.0.0.1/24</p>
                            <p className="text-xs text-success">● Active</p>
                          </>
                        )
                      })()}
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-mono text-success">10.0.0.1/24</p>
                      <p className="text-xs text-success">● Active</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="card p-4 md:p-5">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-cyan" />
              <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary">
                System Health
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-2 md:gap-3">
              <div className="p-2 md:p-3 bg-deep rounded-lg border border-subtle text-center">
                <p className="text-xs text-muted mb-1">CPU</p>
                <p className="text-lg md:text-xl font-mono text-success">
                  {systemStats ? `${(systemStats.cpu_load * 100 / 3).toFixed(0)}%` : '...'}
                </p>
              </div>
              <div className="p-2 md:p-3 bg-deep rounded-lg border border-subtle text-center">
                <p className="text-xs text-muted mb-1">Memory</p>
                <p className="text-lg md:text-xl font-mono text-cyan">
                  {systemStats ? `${(systemStats.memory_used / (1024 * 1024 * 1024)).toFixed(1)}GB` : '...'}
                </p>
              </div>
              <div className="p-2 md:p-3 bg-deep rounded-lg border border-subtle text-center">
                <p className="text-xs text-muted mb-1">Uptime</p>
                <p className="text-lg md:text-xl font-mono text-primary">
                  {systemStats?.uptime_seconds ? formatUptime(systemStats.uptime_seconds) : '...'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardHome