# docker_ctl.py

# packages
import yaml, docker

from docker.models.containers   import Container
from typing                     import Any, Dict, Optional

# functions
def load_scripts(config_path: str) -> Dict[str, dict]:
    """ 2_configs 내 Image 목록을 관리하는 scripts.yaml 불러오기 """
    with open(config_path, "r", encoding="utf-8") as f: data = yaml.safe_load(f) or {}
    scripts = data.get("scripts", [])
    return {s["id"]: s for s in scripts}

def docker_client() -> docker.DockerClient:
    return docker.from_env()

def _normalize_extra_hosts(v: Any) -> Optional[Dict[str, str]]:
    """
    scripts.yaml 의 extra_hosts 값을 Docker SDK 형식(dict: hostname -> ip)으로 정규화.
    - dict 형태: { "my.host.local": "127.0.0.1", "foo.bar": "172.16.0.10" }
    - list 형태: ["my.host.local:127.0.0.1", "foo.bar:172.16.0.10"]
    그 외 입력은 무시(None 반환).
    """
    if not v:               return None
    if isinstance(v, dict): return {str(k): str(v[k]) for k in v} # 모든 값을 문자열로 보장
    if isinstance(v, list):
        out: Dict[str, str] = {}
        for item in v:
            if isinstance(item, str) and ":" in item:
                host, ip = item.split(":", 1)
                host, ip = host.strip(), ip.strip()
                if host and ip: out[host] = ip
        return out or None
    return None


def create_and_start(script: dict, run_id: str) -> Container:
    """ scripts.yaml 내 작성된 이미지를 컨테이너로 실행 """
    cli = docker_client()
    # 이미지 보장
    try:                                cli.images.get(script["image"])
    except docker.errors.ImageNotFound: cli.images.pull(script["image"])

    labels = {
        "app": "N3 Cloud - Web Terminal", "script_id": script["id"], "run_id": run_id,
    }

    # extra_hosts 정규화 (scripts.yaml -> Docker SDK 형식)
    extra_hosts = _normalize_extra_hosts(script.get("extra_hosts"))
    create_kwargs: Dict[str, Any] = {
        "image": script["image"],
        "command": script.get("cmd", ["python", "main.py"]),
        "environment": {
            **script.get("env", {}),
            "OUTPUT_DIR": "/app/out",
            "RUN_ID": run_id,
        },
        "tty": True,
        "stdin_open": True,
        "detach": True,
        "auto_remove": True,   # 종료 시 자동 제거
        "labels": labels,
        # 필요 시 working_dir / user / network / volumes 등 추가 가능
    }

    if script.get("cpu_limit"): create_kwargs["nano_cpus"]   = int(float(script["cpu_limit"]) * 1e9)
    if script.get("mem_limit"): create_kwargs["mem_limit"]   = script["mem_limit"]
    if script.get("cap_add"):   create_kwargs["cap_add"]     = script["cap_add"]
    if extra_hosts:             create_kwargs["extra_hosts"] = extra_hosts

    container: Container = cli.containers.create(**create_kwargs)
    container.start()
    return container

def stop_and_remove(container_id: str):
    cli = docker_client()
    try: c = cli.containers.get(container_id)
    except docker.errors.NotFound: return
    try: c.stop(timeout=2)
    finally:
        try: c.remove()
        except Exception: pass
