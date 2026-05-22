import { useState, useEffect, useCallback } from 'react'
import { Brain, RefreshCw, Download, Trash2 } from 'lucide-react'
import { getMLPredictions, getMLHealth, exportMLPredictions, clearMLPredictions, type MLPrediction, type MLHealth } from '../services/api'
import { useSSE, type SSEMessage } from '../services/sse'

const MLDetection: React.FC = () => {
  const [predictions, setPredictions] = useState<MLPrediction[]>([])
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<MLHealth | null>(null)

  const handleSSE = useCallback((_data: SSEMessage) => {
    fetchPredictions(false)
  }, [])

  useSSE('system_update', handleSSE, true)

  const fetchPredictions = async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const data = await getMLPredictions(100)
      setPredictions(data.predictions || [])
    } catch (err) {
      console.error('Failed to fetch ML predictions:', err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const fetchHealth = async () => {
    try {
      const data = await getMLHealth()
      setHealth(data)
    } catch {
      setHealth({ status: 'offline', models_loaded: 0, models: [], threshold: 0.5 })
    }
  }

  const handleClearPredictions = async () => {
    if (!confirm('Are you sure you want to clear all ML predictions? This cannot be undone.')) return
    try {
      await clearMLPredictions()
      setPredictions([])
    } catch (err) {
      console.error('Failed to clear ML predictions:', err)
    }
  }

  useEffect(() => {
    fetchPredictions()
    fetchHealth()
    const interval = setInterval(() => {
      fetchPredictions(false)
      fetchHealth()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-danger'
    if (conf >= 0.6) return 'text-warning'
    return 'text-success'
  }

  const isHealthy = health?.status === 'healthy' || health?.status === 'ok'

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="card p-4 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex flex-wrap items-center gap-2">
            <Brain className="w-5 h-5 text-cyan flex-shrink-0" />
            <h3 className="text-lg font-[family-name:var(--font-display)] font-semibold text-primary">
              ML Prediction Logs
            </h3>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
              isHealthy 
                ? 'bg-success/10 border border-success/40 text-success' 
                : 'bg-danger/10 border border-danger/40 text-danger'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-success' : 'bg-danger'} ${isHealthy ? 'animate-pulse' : ''}`} />
              {health?.status || 'unknown'}
            </span>
            {health?.models_loaded !== undefined && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan/10 border border-cyan/40 text-cyan text-xs font-semibold">
                {health.models_loaded}/5 models
              </span>
            )}
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button onClick={() => { fetchPredictions(); fetchHealth(); }} className="btn-secondary">
              <RefreshCw className="w-4 h-4 inline mr-1" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            <button onClick={() => exportMLPredictions('json')} className="btn-secondary text-xs" title="Export JSON">
              <Download className="w-4 h-4 inline mr-1" />JSON
            </button>
            <button onClick={() => exportMLPredictions('csv')} className="btn-secondary text-xs" title="Export CSV">
              <Download className="w-4 h-4 inline mr-1" />CSV
            </button>
            <button onClick={handleClearPredictions} className="btn-secondary text-xs text-danger" title="Clear Predictions">
              <Trash2 className="w-4 h-4 inline mr-1" />Clear
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="relative overflow-hidden rounded-lg p-4 bg-deep/80 border border-subtle">
                <div className="flex items-center gap-4">
                  <div className="w-24 h-4 bg-gradient-to-r from-[#1a1a2e] via-[#252540] to-[#1a1a2e] rounded shimmer-animation" />
                  <div className="w-28 h-4 bg-gradient-to-r from-[#1a1a2e] via-[#252540] to-[#1a1a2e] rounded shimmer-animation" />
                  <div className="flex items-center gap-2 ml-auto">
                    <div className="w-12 h-4 bg-gradient-to-r from-[#1a1a2e] via-[#252540] to-[#1a1a2e] rounded shimmer-animation" />
                    <div className="w-12 h-4 bg-gradient-to-r from-[#1a1a2e] via-[#252540] to-[#1a1a2e] rounded shimmer-animation" />
                    <div className="w-12 h-4 bg-gradient-to-r from-[#1a1a2e] via-[#252540] to-[#1a1a2e] rounded shimmer-animation" />
                    <div className="w-14 h-4 bg-gradient-to-r from-[#ff95001a] via-[#ff950033] to-[#ff95001a] rounded shimmer-animation" />
                  </div>
                  <div className="w-14 h-6 rounded-full bg-gradient-to-r from-cyan/10 via-cyan/20 to-cyan/10 shimmer-animation border border-cyan/40" />
                </div>
              </div>
            ))}
          </div>
        ) : predictions.length === 0 ? (
          <div className="text-center py-8 text-muted">
            <Brain className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No ML predictions yet</p>
            <p className="text-xs text-gray-600 mt-1">ML analysis runs on specific attack signatures</p>
          </div>
        ) : (
          <div className="hidden lg:block overflow-x-auto -mx-4 px-4">
              <table className="w-full min-w-0">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Src IP</th>
                  <th>RF</th>
                  <th>XGB</th>
                  <th>DT</th>
                  <th>LR</th>
                  <th>CatB</th>
                  <th>Ensemble</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((pred) => (
                  <tr key={pred.id}>
                    <td className="font-mono text-xs text-muted whitespace-nowrap">
                      {pred.timestamp}
                    </td>
                    <td className="font-mono text-cyan text-sm">{pred.source_ip}</td>
                    <td className="font-mono text-xs">{pred.models.rf.toFixed(2)}</td>
                    <td className="font-mono text-xs">{pred.models.xgb.toFixed(2)}</td>
                    <td className="font-mono text-xs">{pred.models.decision_tree.toFixed(2)}</td>
                    <td className="font-mono text-xs">{pred.models.logistic_regression.toFixed(2)}</td>
                    <td className="font-mono text-xs">{pred.models.catboost.toFixed(2)}</td>
                    <td className={`font-mono text-xs font-bold ${getConfidenceColor(pred.ensemble_score)}`}>
                      {pred.ensemble_score.toFixed(2)}
                    </td>
                    <td>
                      <span className={`badge ${
                        pred.action === 'block' ? 'badge-danger' : pred.action === 'alert' ? 'badge-warning' : 'badge-info'
                      } text-xs`}>
                        {pred.action}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {predictions.length > 0 && (
          <div className="lg:hidden space-y-3">
            {predictions.map((pred) => (
              <div key={pred.id} className="bg-deep rounded-lg border border-subtle p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-cyan font-semibold">{pred.source_ip}</span>
                  <span className={`badge ${
                    pred.action === 'block' ? 'badge-danger' : pred.action === 'alert' ? 'badge-warning' : 'badge-info'
                  } text-xs`}>
                    {pred.action}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-2 mb-3 text-center">
                  <div className="bg-card-hover rounded p-2">
                    <p className="text-muted text-xs">RF</p>
                    <p className="font-mono text-sm">{pred.models.rf.toFixed(2)}</p>
                  </div>
                  <div className="bg-card-hover rounded p-2">
                    <p className="text-muted text-xs">XGB</p>
                    <p className="font-mono text-sm">{pred.models.xgb.toFixed(2)}</p>
                  </div>
                  <div className="bg-card-hover rounded p-2">
                    <p className="text-muted text-xs">DT</p>
                    <p className="font-mono text-sm">{pred.models.decision_tree.toFixed(2)}</p>
                  </div>
                  <div className="bg-card-hover rounded p-2">
                    <p className="text-muted text-xs">LR</p>
                    <p className="font-mono text-sm">{pred.models.logistic_regression.toFixed(2)}</p>
                  </div>
                  <div className="bg-card-hover rounded p-2">
                    <p className="text-muted text-xs">CatB</p>
                    <p className="font-mono text-sm">{pred.models.catboost.toFixed(2)}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-muted text-xs">{pred.timestamp}</p>
                  <p className={`font-mono text-xs font-bold ${getConfidenceColor(pred.ensemble_score)}`}>
                    ENS: {pred.ensemble_score.toFixed(2)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default MLDetection