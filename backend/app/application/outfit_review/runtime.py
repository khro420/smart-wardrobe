"""Opt-in, one-request owned llama.cpp worker. No downloads or service changes."""
import base64
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
import socket
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock
import time
import urllib.request

from .contract import ModelRun, Prediction
from .model import SYSTEM_PROMPT, USER_PROMPT, observe
from .service import ReviewError

ASSETS = {
    "Qwen3VL-4B-Instruct-Q4_K_M.gguf": "66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a",
    "mmproj-Qwen3VL-4B-Instruct-F16.gguf": "256f3a43bd4205ffef48d6b92715e1e70b5b0e9aef06522584967513a9985331",
}
RUNTIME_SHA256 = "38c5affb81c9a8f88f5538c7d11bc445e13bc46a2c6eda05694b8b31a8d45995"
LOCAL_LOCK = Lock()


def enabled():
    return os.getenv("SMART_WARDROBE_OUTFIT_REVIEW_ENABLED", "false").lower() == "true"


def paths():
    cache = Path(os.getenv("LOCALAPPDATA", Path.home()/".cache"))/"SmartWardrobe/model-cache/phase3b"
    folder = Path(os.getenv("SMART_WARDROBE_OUTFIT_REVIEW_MODEL_DIR", str(cache)))
    executable = Path(os.getenv("SMART_WARDROBE_OUTFIT_REVIEW_LLAMA_SERVER", str(folder/"cuda/llama-server.exe")))
    return folder, executable


class QwenObserver:
    def __init__(self):
        self.verified = {}

    def assets_available(self):
        folder, executable = paths()
        return executable.is_file() and all((folder/name).is_file() for name in ASSETS)

    def _verify(self):
        folder, executable = paths()
        for path, expected in [(folder/name, expected) for name, expected in ASSETS.items()] + [(executable, RUNTIME_SHA256)]:
            if not path.is_file():
                raise ReviewError("ModelUnavailable", "The pinned local Qwen4B/runtime assets are unavailable. Reuse the approved offline setup; nothing is downloaded automatically.", 503)
            stat = path.stat()
            key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
            if key not in self.verified:
                with path.open("rb") as f:
                    if file_digest(f, "sha256").hexdigest() != expected:
                        raise ReviewError("ModelUnavailable", "Local vision assets differ from the pinned verified bundle.", 503)
                self.verified = {k: v for k, v in self.verified.items() if k[0] != key[0]}
                self.verified[key] = expected
        return folder, executable

    def __call__(self, image, png):
        return self.guarded(lambda folder,executable:self._run(image,png,folder,executable))

    def guarded(self, execute):
        # Reuse Student 1's existing process-wide admission lock without changing
        # its behavior. Never queue a competing review behind another GPU job.
        from app.infrastructure.ai.gpu_runtime import _GPU_LOCK
        if not enabled():
            raise ReviewError("Disabled", "AI Outfit Review is not enabled on this backend.", 503)
        if not LOCAL_LOCK.acquire(blocking=False):
            raise ReviewError("GpuBusy", "Another outfit observation is active.")
        acquired = False
        try:
            acquired = _GPU_LOCK.acquire(blocking=False)
            if not acquired:
                raise ReviewError("GpuBusy", "Wardrobe processing or virtual try-on is using the GPU. Wait until it finishes.")
            folder, executable = self._verify()
            if os.name != "nt":
                raise ReviewError("GuardUnavailable", "This pinned prototype requires the Windows GPU activity guard.", 503)
            return execute(folder, executable)
        finally:
            if acquired:
                _GPU_LOCK.release()
            LOCAL_LOCK.release()

    def _run(self, image, png, folder, executable, *, task=None):
        from .guard import Guard, discover_backend
        from .windows_job import OwnedJob
        proc = None
        # No photo is written here. Monitoring/native logs are deleted with this
        # private temporary directory, even on failed/terminated inference.
        with TemporaryDirectory(prefix="aura-review-worker-") as temporary:
            try:
                with OwnedJob() as lifetime, Guard(Path(temporary), discover_backend(), monitor_job=lifetime) as guard:
                    guard.preflight()
                    with socket.socket() as reserve:
                        reserve.bind(("127.0.0.1", 0))
                        port = reserve.getsockname()[1]
                    command = [str(executable), "-m", str(folder/next(iter(ASSETS))), "--mmproj", str(folder/"mmproj-Qwen3VL-4B-Instruct-F16.gguf"),
                        "--host", "127.0.0.1", "--port", str(port), "--no-webui", "--ctx-size", "6144", "--parallel", "1", "--threads", "4",
                        "--batch-size", "128", "--ubatch-size", "128", "--flash-attn", "on", "--image-min-tokens", "1024", "--image-max-tokens", "1024",
                        "--fit", "off", "--gpu-layers", "16", "--cache-ram", "0", "--no-mmproj-offload", "--verbosity", "0"]
                    def request(endpoint, body=None, timeout=5):
                        guard.safe()
                        import psutil
                        allowed = {proc.pid, *(p.pid for p in psutil.Process(proc.pid).children(recursive=True))}
                        listeners = {c.pid for c in psutil.net_connections(kind="tcp") if c.status == "LISTEN" and c.laddr.port == port}
                        if listeners and not listeners <= allowed:
                            raise ReviewError("WorkerIdentity", "The inference port is not owned by this review worker.", 503)
                        payload = None if body is None else json.dumps(body).encode()
                        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}"+endpoint, data=payload,
                            headers={"Content-Type": "application/json"}), timeout=timeout) as response:
                            raw = response.read(256*1024+1)
                            if len(raw) > 256*1024:
                                raise ValueError("Oversized inference response")
                            return json.loads(raw)
                    with (Path(temporary)/"native.log").open("w") as native:
                        try:
                            with guard.lock:
                                proc = subprocess.Popen(command, cwd=executable.parent, stdout=native, stderr=subprocess.STDOUT, creationflags=0x08000000)
                                guard.attach(proc)
                                lifetime.attach(proc.pid)
                            deadline = time.monotonic()+180
                            while True:
                                guard.safe()
                                if proc.poll() is not None:
                                    raise RuntimeError("Owned model worker ended")
                                try:
                                    if request("/health").get("status") == "ok":
                                        break
                                except (OSError, ValueError):
                                    pass
                                if time.monotonic() > deadline:
                                    raise TimeoutError("Model startup deadline")
                                time.sleep(.5)
                            settings = {"temperature": .7, "top_p": .8, "top_k": 20, "presence_penalty": 1.5,
                                "repeat_penalty": 1, "min_p": 0, "seed": 42, "max_tokens": 2000, "cache_prompt": False,
                                "response_format": {"type": "json_schema", "json_schema": {"name": "outfit_review_v1", "strict": True, "schema": Prediction.model_json_schema()}},
                                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": [
                                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,"+base64.b64encode(png).decode()}},
                                    {"type": "text", "text": USER_PROMPT}]}]}
                            if task is not None:
                                settings['response_format']={'type':'json_schema','json_schema':{'name':task['name'],'strict':True,'schema':task['schema']}}
                                settings['messages']=task['messages']
                            prompt_text=SYSTEM_PROMPT+'\n'+USER_PROMPT if task is None else json.dumps(task['messages'],sort_keys=True)
                            started = time.perf_counter()
                            response = request("/v1/chat/completions", settings, 300)
                            guard.safe()
                            raw = response["choices"][0]["message"]["content"]
                            run = ModelRun(model="Qwen3-VL-4B-Instruct-Q4_K_M", revision="1cd86afb9a95c410a6038ab3b40d8b578c892266",
                                weights_sha256=ASSETS[next(iter(ASSETS))], projector_sha256=ASSETS["mmproj-Qwen3VL-4B-Instruct-F16.gguf"],
                                runtime="llama.cpp", runtime_build="b12359-b1b770d90", runtime_executable_sha256=RUNTIME_SHA256,
                                settings_sha256=sha256(json.dumps({"request": settings, "command": command},sort_keys=True).encode()).hexdigest(),
                                prompt_sha256=sha256(prompt_text.encode()).hexdigest(),
                                run_id=sha256((image.original_sha256+str(time.time_ns())).encode()).hexdigest()[:32], generated_at=datetime.now(timezone.utc).isoformat())
                            try:
                                if response["choices"][0]["finish_reason"] != "stop":
                                    raise ValueError("Incomplete model output")
                                return observe(image, run, raw) if task is None else task['parse'](raw,run)
                            except ValueError:
                                error = ReviewError(task.get('error_code','InvalidObservation') if task else 'InvalidObservation',
                                    task.get('error_message','The model proposal could not be validated. Its raw proposal is retained temporarily, but cannot be confirmed.') if task else 'The model proposal could not be validated. Its raw proposal is retained temporarily, but cannot be confirmed.',422)
                                error.raw_response = raw[:65536]
                                error.model_run = run.model_dump(mode="json")
                                raise error from None
                        finally:
                            if proc is not None:
                                if proc.poll() is None:
                                    proc.terminate()
                                try:
                                    proc.wait(timeout=15)
                                except subprocess.TimeoutExpired:
                                    proc.kill()
                                    proc.wait(timeout=10)
            except ReviewError:
                raise
            except Exception:
                message="Vision stopped or could not start safely. Close games, wait for processing/try-on to finish, and ensure sufficient RAM/VRAM. No review was confirmed."
                if task and task.get('error_code')=='InvalidAssessment':
                    message="AI feedback stopped or could not start safely. Wait for GPU availability and sufficient RAM/VRAM. Your confirmed outfit details are retained; no assessment score was accepted. You can choose the CPU-only summary."
                raise ReviewError("ResourceOrRuntimeUnavailable", message, 503) from None


class QwenObserverV11(QwenObserver):
    def _run(self,image,png,folder,executable):
        from . import observation_v11 as visual
        task={'name':'outfit_review_observation_v11','schema':visual.Prediction.model_json_schema(),
              'messages':[{'role':'system','content':visual.SYSTEM_PROMPT},{'role':'user','content':[
                  {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(png).decode()}},
                  {'type':'text','text':visual.USER_PROMPT}]}],
              'parse':lambda raw,run:visual.Observation(image=image,run=run,raw_response=raw,prediction=visual.parse_prediction(raw))}
        return super()._run(image,png,folder,executable,task=task)


class QwenObserverNormalized(QwenObserverV11):
    def _run(self,image,png,folder,executable):
        from . import observation_v11 as visual,output_handling
        task={'name':'outfit_review_observation_v111','schema':output_handling.decoding_schema(),
              'messages':[{'role':'system','content':visual.SYSTEM_PROMPT},{'role':'user','content':[
                  {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(png).decode()}},
                  {'type':'text','text':visual.USER_PROMPT}]}],
              'parse':lambda raw,run:output_handling.observe(image,run,raw)}
        return QwenObserver._run(self,image,png,folder,executable,task=task)


class QwenAssessor(QwenObserver):
    def generate(self,confirmation,occasion):
        from . import assessment
        payload=assessment.request_payload(confirmation,occasion)
        task={'name':'outfit_review_qualitative_judgments','schema':assessment.decoding_schema(confirmation,occasion),
              'messages':[{'role':'system','content':assessment.SYSTEM_PROMPT},{'role':'user','content':json.dumps(payload,sort_keys=True)}],
              'parse':lambda raw,run:assessment.assess(confirmation,occasion,raw,run),
              'error_code':'InvalidAssessment','error_message':'The AI feedback could not be grounded in your confirmed details. No score was accepted. You can retry later or use the basic summary.'}
        return self.guarded(lambda folder,executable:super(QwenAssessor,self)._run(confirmation.review.original.image,b'',folder,executable,task=task))
