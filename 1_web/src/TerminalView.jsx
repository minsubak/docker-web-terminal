import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';
import 'xterm/css/xterm.css';

export default function TerminalView({ wsEndpoint, onConnectionChange }) {
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      convertEol: false,
      // 모노스페이스 권장 (가변폭 폰트는 정렬 깨짐)
      fontFamily: '"D2Coding", "JetBrains Mono", "Cascadia Mono", monospace',
      fontSize: 14,
      letterSpacing: 0,  // 촘촘하게
      lineHeight: 1.05,  // 줄 간격도 약간 촘촘
      disableStdin: false,
    });
    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    term.loadAddon(fitAddon);
    term.open(termRef.current);
    fitAddon.fit();

    const onResize = () => {
      try { fitAddon.fit(); } catch {}
    };
    window.addEventListener('resize', onResize);

    const ws = new WebSocket(wsEndpoint);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      try { onConnectionChange?.(true); } catch {}
      setTimeout(() => { try { fitAddon.fit(); } catch {} }, 10);
    };

    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        const text = new TextDecoder().decode(new Uint8Array(ev.data));
        term.write(text);
      } else {
        term.write(String(ev.data));
      }
    };

    ws.onclose = () => {
      try { onConnectionChange?.(false); } catch {}
      term.write('\r\n[connection closed]\r\n');
    };

    term.onData((d) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(new TextEncoder().encode(d));
      }
    });

    return () => {
      window.removeEventListener('resize', onResize);
      try { ws.close(); } catch {}
      try { term.dispose(); } catch {}
    };
  }, [wsEndpoint, onConnectionChange]);

  return (
    <div
      ref={termRef}
      style={{
        height: 'calc(100vh - 220px)', // 헤더/컨트롤 제외 후 충분 높이
        border: '1px solid #ddd',
        borderRadius: 8,
        background: '#000',
      }}
    />
  );
}
