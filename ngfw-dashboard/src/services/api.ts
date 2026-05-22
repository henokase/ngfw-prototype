const CONTROL_API = 'http://192.168.1.70:5001';
const ML_API = 'http://192.168.1.70:5003';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

export interface Block {
  id: number;
  ip: string;
  reason: string;
  ttl: string;
  timestamp: string;
}

export interface Log {
  id: number;
  timestamp: string;
  source: string;
  event: string;
  data: {
    source?: string;
    action?: string;
    ip?: string;
    src_ip?: string;
    reason?: string;
    ttl?: string;
    [key: string]: unknown;
  };
}

export interface MLPrediction {
  id: number;
  timestamp: string;
  attack_type: string;
  source_ip: string;
  dest_ip: string;
  confidence: number;
  ensemble_score: number;
  models: {
    rf: number;
    xgb: number;
    decision_tree: number;
    logistic_regression: number;
    catboost: number;
  };
  action: string;
}

export interface MalwareAlert {
  id: number;
  timestamp: string;
  filename: string;
  signature: string;
  source_ip: string;
  action: string;
}

export interface SystemStats {
  cpu_load: number;
  memory_total: number;
  memory_used: number;
  memory_percent: number;
  uptime: string;
  uptime_seconds: number;
  events_today: number;
  active_threats: number;
}

export interface NetworkStats {
  packets_in: number;
  packets_out: number;
  bytes_in: number;
  bytes_out: number;
  connections: number;
  interfaces: {
    name: string;
    ip: string;
    status: string;
    mac: string;
  }[];
}

export interface FirewallRules {
  input: number;
  output: number;
  forward: number;
}

export interface Service {
  name: string;
  displayName: string;
  port: number | null;
  status: 'active' | 'inactive';
}

export interface MLHealth {
  status: string;
  models_loaded: number;
  models: string[];
  threshold: number;
}

export interface Health {
  status: string;
  db: string;
  total_events_today: number;
  active_threats: number;
  total_blocked_ips: number;
}

export const getHealth = (): Promise<Health> =>
  fetchJson<Health>(`${CONTROL_API}/api/health`);

export const getBlocks = (): Promise<{ success: boolean; blocks: Block[]; total: number }> =>
  fetchJson(`${CONTROL_API}/api/list_blocks`);

export const blockIP = (ip: string, reason: string, ttl: string): Promise<{ success: boolean; blocked_ip: string }> =>
  fetchJson(`${CONTROL_API}/api/block_ip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip, reason, ttl, source: 'Admin' }),
  });

export const unblockIP = (ip: string): Promise<{ success: boolean; unblocked_ip: string }> =>
  fetchJson(`${CONTROL_API}/api/unblock_ip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip, source: 'Admin' }),
  });

export const clearAllBlocks = (): Promise<{ success: boolean; rows_deleted: number }> =>
  fetchJson(`${CONTROL_API}/api/clear_all_blocks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: 'Admin' }),
  });

export const getLogs = (
  limit = 50,
  offset = 0,
  search?: string,
  severity?: string
): Promise<{ success: boolean; logs: Log[]; total: number; limit: number; offset: number }> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (search) params.append('search', search);
  if (severity && severity !== 'all') params.append('severity', severity);
  return fetchJson(`${CONTROL_API}/api/logs?${params}`);
};

export const getMLPredictions = (limit = 100): Promise<{ success: boolean; predictions: MLPrediction[]; total: number }> =>
  fetchJson(`${CONTROL_API}/api/ml_predictions?limit=${limit}`);

export const getMalwareAlerts = (
  limit = 100,
  search?: string
): Promise<{ success: boolean; alerts: MalwareAlert[]; total: number }> => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.append('search', search);
  return fetchJson(`${CONTROL_API}/api/malware_alerts?${params}`);
};

export const clearMalwareAlerts = (): Promise<{ success: boolean; deleted: number }> =>
  fetchJson(`${CONTROL_API}/api/malware_alerts/clear`, { method: 'POST' });

export const getSystemStats = (): Promise<{ success: boolean; stats: SystemStats }> =>
  fetchJson(`${CONTROL_API}/api/system/stats`);

export const getNetworkStats = (): Promise<{ success: boolean; stats: NetworkStats }> =>
  fetchJson(`${CONTROL_API}/api/network/stats`);

export const getFirewallRules = (): Promise<{ success: boolean; rules: FirewallRules }> =>
  fetchJson(`${CONTROL_API}/api/firewall/rules`);

export const getServices = (): Promise<{ success: boolean; services: Service[] }> =>
  fetchJson(`${CONTROL_API}/api/services`);

export const controlService = (
  service: string,
  action: 'start' | 'stop' | 'restart' | 'status'
): Promise<{ success: boolean; service: string; action: string; output: string }> =>
  fetchJson(`${CONTROL_API}/api/service`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, action, source: 'Admin' }),
  });

export const getMLHealth = (): Promise<MLHealth> =>
  fetchJson(`${ML_API}/health`);

export const exportLogs = async (format: 'json' | 'csv' = 'json') => {
  const response = await fetch(`${CONTROL_API}/api/export/logs?format=${format}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `logs_export.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};

export const exportMLPredictions = async (format: 'json' | 'csv' = 'json') => {
  const response = await fetch(`${CONTROL_API}/api/export/ml_predictions?format=${format}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ml_predictions_export.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};

export const exportMalwareAlerts = async (format: 'json' | 'csv' = 'json') => {
  const response = await fetch(`${CONTROL_API}/api/export/malware_alerts?format=${format}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `malware_alerts_export.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};

export const clearLogs = (): Promise<{ success: boolean; deleted: number }> =>
  fetchJson(`${CONTROL_API}/api/logs/clear`, { method: 'POST' });

export const clearMLPredictions = (): Promise<{ success: boolean; deleted: number }> =>
  fetchJson(`${CONTROL_API}/api/ml_predictions/clear`, { method: 'POST' });
