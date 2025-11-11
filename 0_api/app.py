import os, asyncio, uuid, io, tarfile, yaml

from typing             import Literal

from fastapi            import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Path as FPath
from fastapi.responses  import JSONResponse, StreamingResponse

from models             import ScriptItem, StartRequest, StartResponse, StopResponse
from docker_ctl         import load_scripts, create_and_start, stop_and_remove, docker_client

# --- FastAPI -------------------------------------------------------------
app = FastAPI(title="Docker Web Terminal API")

# --- Config 로딩 ---------------------------------------------------------
SCRIPTS_CONFIG_PATH = os.getenv("SCRIPTS_CONFIG", "/configs/scripts.yaml")

def load_config_yaml() -> dict:
    try:
        with open(SCRIPTS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        # 문제 시 빈 dict와 함께 에러 힌트를 포함해도 됨
        return {"_error": str(e)}

# 프런트에서 필요하다면 원본 전체(JSON으로) 받기
@app.get("/config")
def get_raw_config():
    cfg = load_config_yaml()
    return JSONResponse(cfg)

# 프런트에서 실제로 쓰는 값만 깔끔히 전달 (예: scripts 섹션)
@app.get("/ui-config")
def get_ui_config():
    cfg = load_config_yaml()
    return {"scripts": cfg.get("scripts", [])}

# --- 기존 스크립트 목록/실행 ---------------------------------------------
SCRIPTS = load_scripts(SCRIPTS_CONFIG_PATH)

@app.get("/scripts", response_model=list[ScriptItem])
def list_scripts():
    # yaml 변경을 실시간 반영하고 싶으면 아래 2줄로 동적 로딩해도 됨
    # global SCRIPTS
    # SCRIPTS = load_scripts(SCRIPTS_CONFIG_PATH)
    return list(SCRIPTS.values())

@app.post("/run", response_model=StartResponse)
def run_script(req: StartRequest):
    script = SCRIPTS.get(req.script_id)
    if not script:
        raise HTTPException(404, "script not found")
    run_id = uuid.uuid4().hex
    c = create_and_start(script, run_id)
    return {"container_id": c.id, "run_id": run_id}

@app.post("/stop/{container_id}", response_model=StopResponse)
def stop(container_id: str):
    stop_and_remove(container_id)
    return {"ok": True}

# --- WebSocket (attach/exec) ---------------------------------------------
@app.websocket("/ws/{container_id}")
async def ws_attach_or_exec(
    ws: WebSocket,
    container_id: str,
    mode: Literal["attach", "exec"] = Query("attach"),
    cmd: str | None = Query(None),
):
    await ws.accept()
    cli = docker_client()
    container = cli.containers.get(container_id)

    sock = None
    try:
        if mode == "attach":
            params = {"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1, "logs": 1}
            sock = cli.api.attach_socket(container.id, params=params)
        else:
            exec_cmd = ["/bin/sh"] if not cmd else ["/bin/sh", "-lc", cmd]
            exec_id = cli.api.exec_create(container.id, cmd=exec_cmd, tty=True, stdin=True)["Id"]
            sock = cli.api.exec_start(exec_id, tty=True, socket=True)

        raw = sock._sock
        raw.setblocking(False)

        async def ws_to_container():
            try:
                while True:
                    data = await ws.receive_bytes()
                    try:
                        raw.sendall(data)
                    except (BlockingIOError, InterruptedError): await asyncio.sleep(0)
            except WebSocketDisconnect: pass
            except Exception:           pass

        async def container_to_ws():
            try:
                while True:
                    try:
                        chunk = raw.recv(4096)
                    except (BlockingIOError, InterruptedError):
                        await asyncio.sleep(0.01)
                        continue
                    if not chunk: break
                    await ws.send_bytes(chunk)
            except Exception: pass
            finally:
                try: sock.close()
                except Exception: pass

        await asyncio.gather(ws_to_container(), container_to_ws())
    finally:
        try:
            if sock: sock.close()
        except Exception: pass
        asyncio.create_task(async_stop_later(container_id, delay=30))

async def async_stop_later(container_id: str, delay: int = 30):
    await asyncio.sleep(delay)
    try:
        cli = docker_client()
        c = cli.containers.get(container_id)
        c.stop(timeout=2)
    except Exception: pass

# --- 최신 아티팩트 다운로드 (컨테이너 내부에서 직접 찾기) ---------------
def _iter_tar_file_bytes(tar_stream):
    bio = io.BytesIO()
    for chunk in tar_stream:
        bio.write(chunk)
    bio.seek(0)
    with tarfile.open(fileobj=bio, mode="r|*") as tf:
        for member in tf:
            if member.isfile():
                f = tf.extractfile(member)
                if f:
                    data = f.read()
                    return data, member.name.rsplit("/", 1)[-1]
    return b"", "artifact.bin"

def _find_latest_in_container(container, search_roots):
    py = r"""
import os, sys
roots = sys.argv[1:]
c=[]
for root in roots:
    if os.path.isdir(root):
        for R,_,Fs in os.walk(root):
            for f in Fs:
                p=os.path.join(R,f)
                try:c.append((os.path.getmtime(p),p))
                except:pass
if not c:
    print("",end="")
else:
    c.sort(reverse=True)
    print(c[0][1],end="")
"""
    cmd = ["/bin/sh", "-lc", f'python - <<\'PY\' {" ".join(search_roots)}\n{py}\nPY']
    res = container.exec_run(cmd, tty=False)
    if res.exit_code == 0:
        path = (res.output or b"").decode(errors="ignore").strip()
        return path or None
    return None

@app.get("/runs/{run_id}/latest")
def download_latest_by_run(run_id: str = FPath(...)):
    cli = docker_client()
    items = cli.containers.list(all=True, filters={"label": f"run_id={run_id}"})
    if not items: return JSONResponse({"detail": "no files"}, status_code=404)

    container = items[0]
    latest_path = _find_latest_in_container(container, ["/app/out", "/out"])
    if not latest_path: return JSONResponse({"detail": "no files"}, status_code=404)

    try: stream, _ = cli.api.get_archive(container.id, path=latest_path)
    except Exception: return JSONResponse({"detail": "no files"}, status_code=404)

    data, fname = _iter_tar_file_bytes(stream)
    if not data: return JSONResponse({"detail": "no files"}, status_code=404)

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )