import { useEffect, useState } from "react";
import { fetchUIConfig, runScript, wsUrl, downloadLatestByRun } from "./api";
import TerminalView from "./TerminalView";

export default function App() {
  const [scripts, setScripts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [containerId, setContainerId] = useState("");
  const [runId, setRunId] = useState("");
  const [wsEndpoint, setWsEndpoint] = useState("");
  const [wsConnected, setWsConnected] = useState(false);
  const [mode, setMode] = useState("attach");
  const [cmd, setCmd] = useState("python main.py");
  const [error, setError] = useState("");

  // ✅ YAML 직접 호출 금지. 동일 오리진 /api/ui-config 사용
  useEffect(() => {
    fetchUIConfig()
      .then(({ scripts }) => setScripts(scripts || []))
      .catch(e => setError(String(e)));
  }, []);

  const runSelected = async () => {
    if (!selected) return;
    try {
      const r = await runScript(selected.id);
      setContainerId(r.container_id);
      setRunId(r.run_id);
      setWsConnected(false);
      setWsEndpoint(wsUrl(r.container_id, mode, mode === "exec" ? cmd : ""));
    } catch (e) { setError(String(e)); }
  };

  const greenBtn = (enabled = true) => ({
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid #80e27e',
    background: enabled ? '#8eea8a' : '#bff2bd',
    color: '#064b06',
    fontWeight: 700,
    cursor: enabled ? 'pointer' : 'not-allowed',
  });

  return (
    <div style={{display:'flex', flexDirection:'column', minHeight:'100vh', background:'#fff', color:'#1a1a1a'}}>
      <header style={{padding:'12px 20px', borderBottom:'1px solid #e5e7eb'}}>
        <div style={{display:'flex', alignItems:'center', gap:12}}>
          <div style={{fontWeight:800, fontSize:18}}>Docker Web Terminal</div>
          <div style={{opacity:.7, fontSize:13}}>Run images with interactive terminal</div>
        </div>
      </header>

      <div style={{display:'grid', gridTemplateColumns:'300px 1fr', flex:1, minHeight:0}}>
        <aside style={{borderRight:'1px solid #e5e7eb', padding:16, overflow:'auto', background:'#fff'}}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
            <div style={{fontWeight:700}}>Images</div>
            <div style={{fontSize:12, opacity:.6}}>{scripts.length}</div>
          </div>

          <div style={{marginTop:12, display:'grid', gap:8}}>
            {scripts.map(s => {
              const active = selected?.id === s.id;
              return (
                <button key={s.id} onClick={()=>setSelected(s)}
                  style={{
                    textAlign:'left', padding:12, borderRadius:8,
                    border:'1px solid #e5e7eb',
                    background: active ? '#d9d9d9' : '#f0f0f0',
                    color:'#1a1a1a', cursor:'pointer'
                  }}>
                  <div style={{fontWeight:700, fontSize:14}}>{s.title}</div>
                  <div style={{fontSize:12, opacity:.7, marginTop:2}}>{s.image}</div>
                </button>
              );
            })}
          </div>

          <div style={{marginTop:16, paddingTop:16, borderTop:'1px solid #e5e7eb', display:'grid', gap:8}}>
            <label style={{fontSize:12, opacity:.8}}>Mode</label>
            <select value={mode} onChange={e=>setMode(e.target.value)} style={{
              background:'#fff', color:'#1a1a1a', border:'1px solid #e5e7eb', borderRadius:8, padding:'6px 8px'
            }}>
              <option value="attach">attach</option>
              <option value="exec">exec</option>
            </select>

            {mode === "exec" && (
              <>
                <label style={{fontSize:12, opacity:.8, marginTop:8}}>Exec Command</label>
                <input
                  value={cmd}
                  onChange={e=>setCmd(e.target.value)}
                  placeholder="python main.py"
                  style={{
                    background:'#fff', color:'#1a1a1a', border:'1px solid #e5e7eb',
                    borderRadius:8, padding:'6px 8px'
                  }}
                />
              </>
            )}

            <button onClick={runSelected} disabled={!selected} style={greenBtn(!!selected)}>
              Run Selected
            </button>

            {runId && (
              <button
                onClick={()=>downloadLatestByRun(runId)}
                disabled={!wsConnected}
                style={greenBtn(wsConnected)}
              >
                Download Latest Artifact
              </button>
            )}

            {error && <div style={{color:'#b91c1c', fontSize:12}}>{error}</div>}
          </div>
        </aside>

        <main style={{padding:16, overflow:'hidden', background:'#fff'}}>
          {!wsEndpoint ? (
            <div style={{
              height:'calc(100vh - 180px)',
              border:'1px dashed #e5e7eb', borderRadius:8,
              display:'grid', placeItems:'center', color:'#6b7280', background:'#fafafa'
            }}>
              왼쪽에서 이미지를 선택하고 실행하세요.
            </div>
          ) : (
            <div style={{
              border:'1px solid #e5e7eb', borderRadius:8, background:'#fafafa',
              padding:12, height:'calc(100vh - 180px)', display:'flex', flexDirection:'column'
            }}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                <div style={{fontWeight:700}}>Interactive Terminal</div>
                <div style={{fontSize:12, opacity:.7}}>CID: {containerId.slice(0,12)}</div>
              </div>

              {runId && (
                <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:8}}>
                  <button
                    onClick={()=>downloadLatestByRun(runId)}
                    disabled={!wsConnected}
                    style={greenBtn(wsConnected)}
                  >
                    Download Latest Artifact
                  </button>
                  {!wsConnected && (
                    <span style={{fontSize:12, color:'#6b7280'}}>터미널 연결 후 다운로드 가능</span>
                  )}
                </div>
              )}

              <div style={{flex:1, minHeight:0}}>
                <TerminalView
                  wsEndpoint={wsEndpoint}
                  onConnectionChange={setWsConnected}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
