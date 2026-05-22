import { useState, useEffect, useCallback } from 'react'
import { Shield, Plus, Trash2, RefreshCw } from 'lucide-react'
import { getBlocks, blockIP, unblockIP, clearAllBlocks, type Block } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'
import ConfirmModal from './ConfirmModal'

const FirewallManagement: React.FC = () => {
  const [blocks, setBlocks] = useState<Block[]>([])
  const [loading, setLoading] = useState(true)
  const [newIP, setNewIP] = useState('')
  const [reason, setReason] = useState('')
  const [ttl, setTtl] = useState('1h')
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const [modalOpen, setModalOpen] = useState(false)
  const [modalAction, setModalAction] = useState<'block' | 'unblock' | 'clear'>('block')
  const [modalTarget, setModalTarget] = useState('')

  const handleSSE = useCallback((data: SSEMessage) => {
    if (data.blocks) {
      setBlocks(data.blocks.map(b => ({
        id: b.id,
        ip: b.ip,
        reason: b.reason,
        ttl: b.ttl,
        timestamp: b.timestamp,
      })))
    }
  }, [])

  useSSE('system_update', handleSSE, true)

  const fetchBlocks = async () => {
    try {
      const data = await getBlocks()
      setBlocks(data.blocks || [])
    } catch (err) {
      console.error('Failed to fetch blocks:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBlocks()
    const interval = setInterval(fetchBlocks, 10000)
    return () => clearInterval(interval)
  }, [])

  const openBlockModal = () => {
    if (!newIP) return
    setModalAction('block')
    setModalTarget(newIP)
    setModalOpen(true)
  }

  const openUnblockModal = (ip: string) => {
    setModalAction('unblock')
    setModalTarget(ip)
    setModalOpen(true)
  }

  const openClearAllModal = () => {
    setModalAction('clear')
    setModalTarget('')
    setModalOpen(true)
  }

  const handleBlock = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newIP) return

    setActionLoading(true)
    setMessage(null)

    try {
      await blockIP(newIP, reason, ttl)
      setMessage({ type: 'success', text: `IP ${newIP} blocked successfully` })
      setNewIP('')
      setReason('')
      fetchBlocks()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to block IP' })
    } finally {
      setActionLoading(false)
      setModalOpen(false)
    }
  }

  const handleUnblock = async () => {
    setActionLoading(true)
    setMessage(null)

    try {
      await unblockIP(modalTarget)
      setMessage({ type: 'success', text: `IP ${modalTarget} unblocked successfully` })
      fetchBlocks()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to unblock IP' })
    } finally {
      setActionLoading(false)
      setModalOpen(false)
    }
  }

  const handleClearAll = async () => {
    setActionLoading(true)
    setMessage(null)

    try {
      await clearAllBlocks()
      setMessage({ type: 'success', text: 'All blocked IPs cleared' })
      fetchBlocks()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to clear blocks' })
    } finally {
      setActionLoading(false)
      setModalOpen(false)
    }
  }

  const handleModalConfirm = () => {
    if (modalAction === 'unblock') {
      handleUnblock()
    } else if (modalAction === 'clear') {
      handleClearAll()
    } else if (modalAction === 'block') {
      handleBlock({ preventDefault: () => {} } as React.FormEvent)
    }
  }

  const getModalConfig = () => {
    switch (modalAction) {
      case 'block':
        return {
          title: 'Block IP Address',
          message: `Are you sure you want to block ${modalTarget}? This IP will be blocked based on the selected TTL duration.`,
          confirmText: 'Block IP',
          confirmVariant: 'danger' as const,
        }
      case 'unblock':
        return {
          title: 'Unblock IP Address',
          message: `Are you sure you want to unblock ${modalTarget}? This will remove the IP from the firewall block list.`,
          confirmText: 'Unblock',
          confirmVariant: 'primary' as const,
        }
      case 'clear':
        return {
          title: 'Clear All Blocks',
          message: `Are you sure you want to clear all ${blocks.length} blocked IPs? This action cannot be undone.`,
          confirmText: 'Clear All',
          confirmVariant: 'danger' as const,
        }
    }
  }

  const formatTTL = (ttl: number | string | null | undefined): string => {
    const ttlNum = typeof ttl === 'string' ? parseInt(ttl, 10) : ttl;
    if (!ttlNum) return 'Permanent'
    if (ttlNum >= 86400) return `${Math.floor(ttlNum / 86400)}d`
    if (ttlNum >= 3600) return `${Math.floor(ttlNum / 3600)}h`
    if (ttlNum >= 60) return `${Math.floor(ttlNum / 60)}m`
    return `${ttlNum}s`
  }

  const modalConfig = getModalConfig()

  return (
    <div className="space-y-4 md:space-y-6">
      <ConfirmModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={handleModalConfirm}
        title={modalConfig.title}
        message={modalConfig.message}
        confirmText={modalConfig.confirmText}
        confirmVariant={modalConfig.confirmVariant}
        loading={actionLoading}
      />

      <div className="card p-4 md:p-6">
        <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5 text-cyan" />
          Block New IP
        </h3>

        <form onSubmit={(e) => { e.preventDefault(); openBlockModal(); }} className="flex flex-col sm:flex-row flex-wrap gap-3 md:gap-4 items-end">
          <div className="flex-1 min-w-[140px] w-full sm:w-auto">
            <label className="block text-xs text-muted mb-1">IP Address</label>
            <input
              type="text"
              value={newIP}
              onChange={(e) => setNewIP(e.target.value)}
              placeholder="192.168.1.100"
              className="w-full"
            />
          </div>
          <div className="flex-1 min-w-[140px] w-full sm:w-auto">
            <label className="block text-xs text-muted mb-1">Reason</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Suspicious activity"
              className="w-full"
            />
          </div>
          <div className="w-full sm:w-28">
            <label className="block text-xs text-muted mb-1">TTL</label>
            <select value={ttl} onChange={(e) => setTtl(e.target.value)} className="w-full">
              <option value="1h">1 hour</option>
              <option value="6h">6 hours</option>
              <option value="24h">24 hours</option>
              <option value="7d">7 days</option>
              <option value="permanent">Permanent</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={actionLoading || !newIP}
            onClick={openBlockModal}
            className="btn-primary w-full sm:w-auto min-h-[44px] disabled:opacity-50"
          >
            <Plus className="w-4 h-4 inline mr-1" />
            Block
          </button>
        </form>

        {message && (
          <div className={`mt-4 p-3 rounded-lg text-sm ${
            message.type === 'success' 
              ? 'bg-success/10 text-success border border-success/20' 
              : 'bg-danger/10 text-danger border border-danger/20'
          }`}>
            {message.text}
          </div>
        )}
      </div>

      <div className="card p-4 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan" />
            Active Blocks ({blocks.length})
          </h3>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={fetchBlocks}
              className="btn-secondary text-sm w-full sm:w-auto"
            >
              <RefreshCw className="w-4 h-4 inline mr-1" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            {blocks.length > 0 && (
              <button
                onClick={openClearAllModal}
                disabled={actionLoading}
                className="btn-danger text-sm"
              >
                <Trash2 className="w-4 h-4 inline mr-1" />
                <span className="hidden sm:inline">Clear All</span>
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="relative overflow-hidden rounded-lg p-4 bg-deep/80 border border-subtle">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-border-subtle to-bg-deep flex items-center justify-center border border-border-subtle">
                    <div className="w-4 h-4 rounded-full bg-cyan/20 shimmer-glow" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 shimmer-bg rounded shimmer-animation" />
                    <div className="h-3 w-20 shimmer-bg rounded shimmer-animation" />
                  </div>
                  <div className="w-16 h-6 rounded-full bg-gradient-to-r from-warning/10 via-warning/20 to-warning/10 shimmer-animation border border-warning/40" />
                </div>
              </div>
            ))}
          </div>
        ) : blocks.length === 0 ? (
          <div className="text-center py-8 text-muted">
            <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No blocked IPs</p>
          </div>
        ) : (
          <div className="hidden md:block overflow-x-auto -mx-4 px-4">
            <table className="w-full min-w-0">
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>Reason</th>
                  <th>TTL</th>
                  <th>Blocked At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {blocks.map((block) => (
                  <tr key={block.id}>
                    <td className="font-mono text-cyan text-sm">{block.ip}</td>
                    <td className="text-secondary text-sm">{block.reason || '-'}</td>
                    <td>
                      <span className="badge badge-warning text-xs">{formatTTL(block.ttl)}</span>
                    </td>
                    <td className="text-muted font-mono text-xs whitespace-nowrap">{block.timestamp}</td>
                    <td>
                      <button
                        onClick={() => openUnblockModal(block.ip)}
                        disabled={actionLoading}
                        className="text-danger hover:text-red-400 text-sm disabled:opacity-50 min-h-[44px] px-2"
                      >
                        Unblock
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {blocks.length > 0 && (
          <div className="md:hidden space-y-3">
            {blocks.map((block) => (
              <div key={block.id} className="bg-deep rounded-lg border border-subtle p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-cyan font-semibold">{block.ip}</span>
                  <span className="badge badge-warning text-xs">{formatTTL(block.ttl)}</span>
                </div>
                <p className="text-secondary text-sm mb-2">{block.reason || 'No reason'}</p>
                <p className="text-tertiary text-xs mb-3">{block.timestamp}</p>
                <button
                  onClick={() => openUnblockModal(block.ip)}
                  disabled={actionLoading}
                  className="w-full py-2 rounded-lg bg-danger/10 text-danger hover:bg-danger/20 text-sm disabled:opacity-50 min-h-[44px]"
                >
                  Unblock IP
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default FirewallManagement