import { useState, useEffect, useCallback } from 'react'
import { Network, Wifi, WifiOff, Activity, Upload, Download } from 'lucide-react'
import { getNetworkStats, getFirewallRules, type FirewallRules } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'

interface Interface {
  name: string
  ip: string
  netmask: string
  status: 'up' | 'down'
  mac: string
  type: 'external' | 'internal'
  description: string
}

const defaultInterfaces: Interface[] = [
  { name: 'enp0s3', ip: '192.168.1.70', netmask: '255.255.255.0', status: 'up', mac: '08:00:27:6c:5a:3f', type: 'external', description: 'External - Connected to host/internet' },
  { name: 'enp0s8', ip: '10.0.0.1', netmask: '255.255.255.0', status: 'up', mac: '08:00:27:8a:2b:1d', type: 'internal', description: 'Internal - Connected to test server' },
]

const NetworkOverview: React.FC = () => {
  const [interfaces, setInterfaces] = useState<Interface[]>(defaultInterfaces)
  const [stats, setStats] = useState({
    packetsIn: 0,
    packetsOut: 0,
    bytesIn: 0,
    bytesOut: 0,
    connections: 0,
  })
  const [rules, setRules] = useState<FirewallRules>({ input: 0, output: 0, forward: 0 })

  const handleSSE = useCallback((data: SSEMessage) => {
    if (data.packets_in !== undefined) {
      setStats({
        packetsIn: data.packets_in,
        packetsOut: data.packets_out || 0,
        bytesIn: data.bytes_in || 0,
        bytesOut: data.bytes_out || 0,
        connections: data.connections || 0,
      })
    }
  }, [])

  useSSE('system_update', handleSSE, true)

  const fetchData = async () => {
    try {
      const [networkData, rulesData] = await Promise.all([
        getNetworkStats(),
        getFirewallRules(),
      ])

      if (networkData.success && networkData.stats) {
        const netStats = networkData.stats
        
        const parsedInterfaces: Interface[] = []
        for (const iface of netStats.interfaces || []) {
          parsedInterfaces.push({
            name: iface.name,
            ip: iface.ip,
            netmask: '255.255.255.0',
            status: (iface.status === 'up' ? 'up' : 'down') as 'up' | 'down',
            mac: iface.mac,
            type: (iface.name === 'enp0s3' ? 'external' : 'internal') as 'external' | 'internal',
            description: iface.name === 'enp0s3' ? 'External - Connected to host/internet' : 'Internal - Connected to test server',
          })
        }
        
        if (parsedInterfaces.length > 0) {
          setInterfaces(parsedInterfaces)
        }

        setStats({
          packetsIn: netStats.packets_in || 0,
          packetsOut: netStats.packets_out || 0,
          bytesIn: netStats.bytes_in || 0,
          bytesOut: netStats.bytes_out || 0,
          connections: netStats.connections || 0,
        })
      }

      if (rulesData.success && rulesData.rules) {
        setRules(rulesData.rules)
      }
    } catch (err) {
      console.error('Failed to fetch network data:', err)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4">
        <div className="card p-4 md:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider">Packets In</p>
              <p className="text-xl md:text-2xl font-[family-name:var(--font-display)] font-bold text-cyan">
                {stats.packetsIn.toLocaleString()}
              </p>
            </div>
            <Download className="w-5 md:w-6 h-5 md:h-6 text-cyan opacity-50" />
          </div>
        </div>
        <div className="card p-4 md:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider">Packets Out</p>
              <p className="text-xl md:text-2xl font-[family-name:var(--font-display)] font-bold text-success">
                {stats.packetsOut.toLocaleString()}
              </p>
            </div>
            <Upload className="w-5 md:w-6 h-5 md:h-6 text-success opacity-50" />
          </div>
        </div>
        <div className="card p-4 md:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider">Data Transfer</p>
              <p className="text-xl md:text-2xl font-[family-name:var(--font-display)] font-bold text-primary">
                {formatBytes(stats.bytesIn)} / {formatBytes(stats.bytesOut)}
              </p>
            </div>
            <Activity className="w-5 md:w-6 h-5 md:h-6 text-muted opacity-50" />
          </div>
        </div>
        <div className="card p-4 md:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider">Active Connections</p>
              <p className="text-xl md:text-2xl font-[family-name:var(--font-display)] font-bold text-warning">
                {stats.connections}
              </p>
            </div>
            <Network className="w-5 md:w-6 h-5 md:h-6 text-warning opacity-50" />
          </div>
        </div>
      </div>

      <div className="card p-4 md:p-6">
        <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary mb-4 md:mb-6 flex items-center gap-2">
          <Network className="w-5 h-5 text-cyan" />
          Network Interfaces
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
          {interfaces.map((iface) => (
            <div
              key={iface.name}
              className={`flex flex-col p-4 md:p-5 rounded-lg border ${
                iface.status === 'up'
                  ? 'bg-deep border-success/20'
                  : 'bg-deep border-danger/20'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  {iface.status === 'up' ? (
                    <Wifi className="w-5 h-5 text-success" />
                  ) : (
                    <WifiOff className="w-5 h-5 text-danger" />
                  )}
                  <div>
                    <p className="text-base font-semibold text-primary">{iface.name}</p>
                    <p className="text-xs text-muted">{iface.type.toUpperCase()} Interface</p>
                  </div>
                </div>
                <span className={`badge ${iface.status === 'up' ? 'badge-success' : 'badge-danger'}`}>
                  {iface.status}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between gap-1">
                  <span className="text-muted">IP Address</span>
                  <span className="font-mono text-cyan">{iface.ip || 'N/A'}/24</span>
                </div>
                <div className="flex justify-between gap-1">
                  <span className="text-muted">MAC Address</span>
                  <span className="font-mono text-gray-400">{iface.mac || 'N/A'}</span>
                </div>
                <div className="flex justify-between gap-1">
                  <span className="text-muted">Network</span>
                  <span className="font-mono text-gray-400">
                    {iface.ip ? iface.ip.split('.').slice(0,3).join('.') + '.0/24' : 'N/A'}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-subtle">
                <p className="text-xs text-muted">{iface.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-4 md:p-6">
        <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary mb-4">
          Firewall Rules Summary
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
          <div className="p-3 md:p-4 bg-deep rounded-lg border border-subtle">
            <p className="text-xs text-muted mb-1">INPUT Rules</p>
            <p className="text-xl md:text-2xl font-mono text-cyan">{rules.input}</p>
          </div>
          <div className="p-3 md:p-4 bg-deep rounded-lg border border-subtle">
            <p className="text-xs text-muted mb-1">OUTPUT Rules</p>
            <p className="text-xl md:text-2xl font-mono text-success">{rules.output}</p>
          </div>
          <div className="p-3 md:p-4 bg-deep rounded-lg border border-subtle">
            <p className="text-xs text-muted mb-1">FORWARD Rules</p>
            <p className="text-xl md:text-2xl font-mono text-warning">{rules.forward}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NetworkOverview