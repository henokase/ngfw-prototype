import { useState, useEffect, useCallback, useRef } from 'react'
import { Terminal, Shield, AlertTriangle, Bug, Server, Download, Trash2 } from 'lucide-react'
import { getLogs, exportLogs, clearLogs, type Log } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'

const AttackLogs: React.FC = () => {
  const [logs, setLogs] = useState<Log[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const terminalRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)
  const isInitialLoad = useRef(true)

  const handleSSE = useCallback((data: SSEMessage) => {
    if (data.stats) {
      fetchLogs(false)
    }
  }, [])

  useSSE('system_update', handleSSE, true)

  const fetchLogs = async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const data = await getLogs(1000, 0)
      const newLogs = (data.logs || []).reverse()
      
      if (!isAtBottomRef.current) {
        return
      }
      
      setLogs(newLogs)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to fetch logs:', err)
      setLogs([])
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const handleClearLogs = async () => {
    if (!confirm('Are you sure you want to clear all logs? This cannot be undone.')) return
    try {
      await clearLogs()
      setLogs([])
      setTotal(0)
    } catch (err) {
      console.error('Failed to clear logs:', err)
    }
  }

  useEffect(() => {
    fetchLogs()
    isInitialLoad.current = false
    const interval = setInterval(() => {
      if (isAtBottomRef.current) {
        fetchLogs(false)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (terminalRef.current && isAtBottomRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [logs])

  const handleScroll = () => {
    if (terminalRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = terminalRef.current
      isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 50
    }
  }

  const formatLogLine = (log: Log): { prefix: string; details: string } => {
    const data = log.data
    const source = data.source || log.source || 'unknown'
    const timestamp = log.timestamp.split('T')[1]?.split('.')[0] || ''
    const action = data.action || log.event || 'unknown'

    let prefix = ''
    let details = ''

    if (source === 'decision_engine' || source.includes('engine')) {
      if (action === 'block_ip' || action === 'ml_block') {
        prefix = `${timestamp}`
        details = `BLOCK ${data.ip || '-'} | ${data.reason || '-'}`
      } else if (typeof action === 'string' && action.startsWith('alert_')) {
        prefix = `${timestamp}`
        details = `ALERT ${data.alert_name || action.replace('alert_', '')} | ${data.src_ip || '-'} → ${data.dest_ip || '-'}`
      } else if (action === 'malware_file_detected') {
        prefix = `${timestamp}`
        details = `MALWARE ${data.src_ip || '-'} | ${data.filename || '-'}`
      } else {
        prefix = `${timestamp}`
        details = `${action} | ${data.src_ip || data.ip || '-'}`
      }
    } else if (source === 'Admin') {
      if (action === 'block_ip') {
        prefix = `${timestamp}`
        details = `ADMIN-BLOCK ${data.ip || '-'} | TTL: ${data.ttl || '-'}`
      } else if (action === 'unblock_ip') {
        prefix = `${timestamp}`
        details = `ADMIN-UNBLOCK ${data.ip || '-'}`
      } else if (action === 'clear_all_blocks') {
        prefix = `${timestamp}`
        details = `ADMIN-CLEAR ${data.rows_deleted || 0} IPs`
      } else if (typeof action === 'string' && action.startsWith('service_')) {
        prefix = `${timestamp}`
        details = `SERVICE ${action.replace('service_', '').toUpperCase()} ${data.service || '-'}`
      } else {
        prefix = `${timestamp}`
        details = `${action || 'ADMIN'} | ${Object.entries(data).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).substring(0, 20) : v}`).join(' | ')}`
      }
    } else {
      prefix = `${timestamp}`
      details = `${source} | ${Object.entries(data).slice(0, 4).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).substring(0, 15) : v}`).join(' | ')}`
    }

    return { prefix, details }
  }

  const getLogIcon = (log: Log): { icon: React.ReactElement; color: string } => {
    const data = log.data
    const source = data.source || log.source || ''
    const action = data.action || log.event || ''

    if (source === 'decision_engine' || source.includes('engine')) {
      if (action === 'block_ip' || action === 'ml_block') return { icon: <Shield className="w-3.5 h-3.5" />, color: 'text-danger' }
      if (typeof action === 'string' && action.startsWith('alert_')) return { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: 'text-warning' }
      if (action === 'malware_file_detected') return { icon: <Bug className="w-3.5 h-3.5" />, color: 'text-warning' }
    }

    if (source === 'Admin') return { icon: <Server className="w-3.5 h-3.5" />, color: 'text-success' }

    return { icon: <Terminal className="w-3.5 h-3.5" />, color: 'text-muted' }
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="card p-0 overflow-hidden max-w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-4 border-b border-subtle flex-shrink-0">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-cyan flex-shrink-0" />
            <h3 className="text-base sm:text-lg font-[family-name:var(--font-display)] font-semibold text-primary">
              Detection Logs
            </h3>
            <span className="text-sm sm:text-base text-muted">
              ({total})
            </span>
          </div>
          <div className="flex gap-2">
            <button onClick={() => exportLogs('json')} className="btn-secondary text-xs" title="Export JSON">
              <Download className="w-4 h-4 inline mr-1" />JSON
            </button>
            <button onClick={() => exportLogs('csv')} className="btn-secondary text-xs" title="Export CSV">
              <Download className="w-4 h-4 inline mr-1" />CSV
            </button>
            <button onClick={handleClearLogs} className="btn-secondary text-xs text-danger" title="Clear Logs">
              <Trash2 className="w-4 h-4 inline mr-1" />Clear
            </button>
          </div>
        </div>

        {loading && logs.length === 0 ? (
          <div className="bg-deep p-4 space-y-0">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className={`flex items-start gap-3 py-3 ${i % 2 === 0 ? 'bg-card' : 'bg-transparent'}`}>
                <div className="relative overflow-hidden rounded p-2 bg-border-subtle/50 border border-border-subtle/20">
                  <div className="w-3.5 h-3.5 rounded-full bg-cyan/20 shimmer-glow" />
                </div>
                <div className="flex-1 flex items-center gap-3">
                  <div className="w-20 h-3 shimmer-bg rounded shimmer-animation" />
                  <div className="h-3 shimmer-bg rounded shimmer-animation flex-1 max-w-[400px]" />
                </div>
              </div>
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-muted">
            <Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No logs found</p>
          </div>
        ) : (
          <div 
            ref={terminalRef}
            onScroll={handleScroll}
            className="h-[calc(100dvh-220px)] min-h-[400px] overflow-y-auto bg-deep font-mono text-xs max-w-full"
          >
            {logs.map((log, idx) => {
              const { prefix, details } = formatLogLine(log)
              const { icon, color } = getLogIcon(log)
              return (
                <div 
                  key={log.id}
                  className={`flex items-start gap-2 p-3 break-words whitespace-normal ${idx % 2 === 0 ? 'bg-card' : 'bg-deep'} hover:bg-card-hover`}
                >
                  <span className={`flex-shrink-0 mt-0.5 ${color}`}>{icon}</span>
                  <span className="text-muted whitespace-nowrap flex-shrink-0">{prefix}</span>
                  <span className="text-secondary break-words whitespace-normal">{details}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default AttackLogs