import yaml, docker

from typing                     import Dict
from docker.models.containers   import Container

def load_scripts(config_path: str) -> Dict[str, dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    scripts = data.get("scripts", [])
    return {s["id"]: s for s in scripts}

def docker_client() -> docker.DockerClient:
    return docker.from_env()

def create_and_start(script: dict, run_id: str) -> Container:
    cli = docker_client()
    try:
        cli.images.get(script["image"])
    except docker.errors.ImageNotFound:
        cli.images.pull(script["image"])

    labels = {
        "app": "N3 Cloud - Web Terminal",
        "script_id": script["id"],
        "run_id": run_id,
    }

    create_kwargs = {
        "image": script["image"],
        "command": script.get("cmd", ["python", "main.py"]),
        "environment": {**script.get("env", {}), "OUTPUT_DIR": "/app/out", "RUN_ID": run_id},
        "tty": True,
        "stdin_open": True,
        "detach": True,
        "auto_remove": True,
        "labels": labels,
        # ✅ 볼륨 바인딩 제거: 컨테이너 로컬 파일만 사용
    }

    if script.get("cpu_limit"):
        create_kwargs["nano_cpus"] = int(float(script["cpu_limit"]) * 1e9)
    if script.get("mem_limit"):
        create_kwargs["mem_limit"] = script["mem_limit"]

    container: Container = cli.containers.create(**create_kwargs)
    container.start()
    return container

def stop_and_remove(container_id: str):
    cli = docker_client()
    try:
        c = cli.containers.get(container_id)
    except docker.errors.NotFound:
        return
    try:
        c.stop(timeout=2)
    finally:
        try:
            c.remove()
        except Exception:
            pass
