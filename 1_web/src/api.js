// API 베이스: 상대경로(/api) 또는 절대경로 모두 지원
const RAW_BASE = import.meta.env.VITE_API_BASE || '/api';
const API_BASE = new URL(RAW_BASE, window.location.origin).toString();

export async function fetchUIConfig() {
  const r = await fetch(`${API_BASE}/ui-config`);
  if (!r.ok) throw new Error('Failed to load ui-config');
  return r.json(); // { scripts: [...] }
}

export async function fetchScripts() {
  // 기존 코드 호환용 (ui-config가 이미 scripts를 제공하므로 둘 중 하나만 써도 됨)
  const r = await fetch(`${API_BASE}/scripts`);
  if (!r.ok) throw new Error('Failed to load scripts');
  return r.json();
}

export async function runScript(script_id) {
  const r = await fetch(`${API_BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script_id }),
  });
  if (!r.ok) throw new Error('Run failed');
  return r.json(); // { container_id, run_id }
}

export function wsUrl(containerId, mode='attach', cmd='') {
  const base = new URL(API_BASE, window.location.origin);
  const wsProto = base.protocol === 'https:' ? 'wss:' : 'ws:';
  const u = new URL(base.toString());
  u.protocol = wsProto;
  u.pathname = `/ws/${containerId}`;
  u.searchParams.set('mode', mode);
  if (cmd) u.searchParams.set('cmd', cmd);
  return u.toString();
}

export function downloadLatestByRun(runId) {
  const url = `${API_BASE}/runs/${runId}/latest`;
  window.open(url, '_blank');
}
