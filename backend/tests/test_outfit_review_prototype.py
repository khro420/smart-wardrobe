"""Disposable authenticated prototype tests. Inference doubles are explicit."""
import json
from threading import Event
from io import BytesIO
from PIL import Image
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import outfit_review_routes as routes
from app.application.outfit_review.service import ReviewService, ReviewError
from app.application.outfit_review.contract import Prediction, digest
from app.application.outfit_review.model import observe
from app.application.outfit_review.occasion import Occasion
from app.application.outfit_review.feedback import DIMENSIONS
from tests.test_outfit_review_observation import prediction, item, fact, image_bytes, observation


def observer(image, png):
    return observe(image, observation().run, json.dumps(prediction()))


def occasion(text):
    return Occasion(original_text=text, context="academic.library_study", role="unspecified", dress_code=None,
                    formality=None, grammar="fixture-only-not-model-inference", interpretation_sha256="a"*64, requirements=())


@pytest.fixture
def service():
    instance = ReviewService(observer, occasion, cleanup=False)
    yield instance
    instance.close()


def analyzed(service, owner="alice"):
    view = service.create(owner, image_bytes())
    service.analyze(view["id"], owner, True).result(timeout=3)
    return service.view(view["id"], owner)


@pytest.fixture
def client(service, monkeypatch):
    # Use the actual signed-bearer/revocation boundary against conftest storage.
    from app.infrastructure.persistence.postgresql_repository import initialise_database
    from app.infrastructure.security import issue_access_token
    initialise_database()
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.service] = lambda: service
    monkeypatch.setenv("SMART_WARDROBE_OUTFIT_REVIEW_ENABLED", "true")
    with TestClient(app) as c:
        c.headers["Authorization"] = "Bearer " + issue_access_token("alice")
        yield c


def test_authenticated_end_to_end_upload_confirm_occasion_and_abstention(client, service):
    response = client.post("/api/v1/outfit-reviews", files={"file": ("photo.png", image_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    id = response.json()["id"]
    assert client.get(f"/api/v1/outfit-reviews/{id}/photo").headers["cache-control"] == "no-store"
    assert client.post(f"/api/v1/outfit-reviews/{id}/analyze", json={"gpu_available": False}).status_code == 409
    assert client.post(f"/api/v1/outfit-reviews/{id}/analyze", json={"gpu_available": True}).status_code == 202
    service.executor.submit(lambda: None).result(timeout=3)
    view = client.get(f"/api/v1/outfit-reviews/{id}").json()
    assert view["state"] == "needs_review"
    assert view["result"] is None
    assert client.post(f"/api/v1/outfit-reviews/{id}/review", json={"revision": view["revision"], "occasion": "Library"}).status_code == 409
    response = client.post(f"/api/v1/outfit-reviews/{id}/confirm", json={"revision": view["revision"], "inventory_reviewed": True})
    assert response.status_code == 200, response.text
    assert client.post(f"/api/v1/outfit-reviews/{id}/review", json={"revision": view["revision"], "occasion": "Library"}).status_code == 202
    service.executor.submit(lambda: None).result(timeout=3)
    result = client.get(f"/api/v1/outfit-reviews/{id}").json()["result"]
    assert result["rubric"]["score"] is None
    assert result["rubric"]["weights_redistributed"] is False
    assert [d["weight_percent"] for d in result["rubric"]["dimensions"]] == [40,25,20,15]
    assert sum(weight for _,weight in DIMENSIONS) == 100
    assert result["facts"][0]["category"] == "dress"
    assert result["occasion"]["dress_code"] is None
    assert "none has been assumed" in result["sections"][0]["text"]
    assert not any(word in json.dumps(result).lower() for word in ["attractive", "body shape", "weight loss"])


def test_api_real_json_corrections_are_complete_scoped_and_invalidate_confirmation(client, service):
    view = analyzed(service)
    id, revision = view["id"], view["revision"]
    p = prediction(items=[item(colours=fact("blue"))])
    body = {"revision": revision, "prediction": p, "changes": [{"operation": "replace_item", "subject": "dress", "reason": "I can see blue."}]}
    response = client.patch(f"/api/v1/outfit-reviews/{id}/inventory", json=body)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["original_prediction"]["items"][0]["colours"]["values"] == ["multicoloured"]
    assert updated["prediction"]["items"][0]["colours"]["values"] == ["blue"]
    assert not updated["confirmed"]
    assert client.patch(f"/api/v1/outfit-reviews/{id}/inventory", json=body).status_code == 409
    body["revision"] = updated["revision"]
    body["authority"] = {"user": "alice"}
    assert client.patch(f"/api/v1/outfit-reviews/{id}/inventory", json=body).status_code == 422


@pytest.mark.parametrize("endpoint,method", [("", "get"),("/photo", "get"),("", "delete"),("/confirm", "post"),("/analyze", "post")])
def test_foreign_access_never_sees_or_changes_photo(client, service, endpoint, method):
    from app.infrastructure.security import issue_access_token
    view = analyzed(service)
    client.headers["Authorization"] = "Bearer " + issue_access_token("bob")
    body = {"revision": view["revision"], "inventory_reviewed": True} if endpoint == "/confirm" else {"gpu_available": True}
    response = getattr(client, method)(f"/api/v1/outfit-reviews/{view['id']}"+endpoint, **({"json": body} if method=="post" else {}))
    assert response.status_code == 404, response.text


def test_missing_bearer_cannot_use_development_user_header(client):
    client.headers.pop("Authorization")
    response = client.get("/api/v1/outfit-reviews/capabilities", headers={"X-User-Id": "alice"})
    assert response.status_code == 401


@pytest.mark.parametrize("content,mime", [(b"GIF89a", "image/gif"),(image_bytes(), "image/jpeg"),(b"invalid", "image/png")])
def test_invalid_upload_mime_signature_and_decode(client, content, mime):
    assert client.post("/api/v1/outfit-reviews", files={"file": ("wrong", content, mime)}).status_code in (415,422)


def test_confirmed_inventory_correction_resets_feedback_and_identity_is_immutable(service):
    view = analyzed(service)
    id = view["id"]
    service.confirm(id,"alice",view["revision"],True)
    service.evaluate(id,"alice",view["revision"],"Library").result(timeout=3)
    from app.application.outfit_review.confirmation import Correction
    p = Prediction.model_validate_json(json.dumps(prediction(items=[item(pattern=fact("striped"))])))
    new = service.correct(id,"alice",view["revision"],p,(Correction(operation="replace_item",subject="dress",reason="Visible stripes."),))
    assert new["result"] is None and not new["confirmed"] and new["state"] == "needs_review"
    assert new["original_prediction"] == view["original_prediction"]


def test_structural_contradictions_visible_but_confirmation_refused(service):
    service.observer = lambda image,png: observe(image,observation().run,json.dumps(prediction(items=[item(role="upper")])))
    view = analyzed(service)
    assert "dress:category_role_conflict" in view["issues"]
    assert view["prediction"]["items"][0]["category"] == "dress"
    with pytest.raises(ValueError):service.confirm(view["id"],"alice",view["revision"],True)


@pytest.mark.parametrize("code", ["ModelUnavailable","GpuBusy","ResourceOrRuntimeUnavailable","InvalidObservation"])
def test_runtime_failure_is_explicit_and_has_no_confirmation(service, code):
    def fail(*args):
        error = ReviewError(code,"Safe public error",503)
        error.raw_response = '{"unvalidated":"retained"}'
        raise error
    service.observer = fail
    view = analyzed(service)
    assert view["state"] == "failed" and not view["confirmed"] and view["result"] is None
    assert view["error"]["code"] == code
    assert view["raw_failed_proposal"] == '{"unvalidated":"retained"}'


def test_busy_admission_delete_and_expiry_cannot_commit_an_analysis(service):
    started,finish = Event(),Event()
    def wait(image,png):
        started.set();finish.wait(3);return observer(image,png)
    service.observer=wait
    view=service.create("alice",image_bytes())
    future=service.analyze(view["id"],"alice",True)
    assert started.wait(2)
    with pytest.raises(ReviewError):service.analyze(view["id"],"alice",True)
    service.delete(view["id"],"alice")
    finish.set();future.result(timeout=3)
    with pytest.raises(ReviewError):service.view(view["id"],"alice")
    assert not service.busy


def test_privacy_ttl_capacity_and_service_restart(service):
    now=[0.]
    service.clock=lambda:now[0]
    a=service.create("alice",image_bytes());service.create("alice",image_bytes())
    with pytest.raises(ReviewError) as failure:service.create("alice",image_bytes())
    assert failure.value.code=="Capacity"
    now[0]=901
    with pytest.raises(ReviewError):service.photo(a["id"],"alice")
    assert not service.entries


def test_real_occasion_adapter_uses_original_not_inferred_dress_code(monkeypatch):
    from app.development.mixed_wardrobe import semantic_appearance as source
    from app.application.outfit_review.occasion import interpret
    raw="I have a job interview as a candidate."
    monkeypatch.setattr(source,"propose",lambda text:{"proposal":"fixture"})
    monkeypatch.setattr(source,"document",lambda text,proposal:{"request":{"context":{},"formality":None},
        "evaluation_request":{"formality":"smart_casual"},"interview_default":{"inferred":True},"grammar_version":"fixture",
        "semantic_metadata":{"primary":"professional.job_interview","role":"candidate"},"revision":"a"*64,"hard_intent":None})
    result=interpret(raw)
    assert result.original_text==raw and result.dress_code is None and result.formality is None and not result.inferred_dress_code


def test_occasion_ambiguity_clears_previous_completed_result(service):
    view=analyzed(service);id=view["id"];rev=view["revision"]
    service.confirm(id,"alice",rev,True)
    service.evaluate(id,"alice",rev,"Library").result(timeout=3)
    assert service.view(id,"alice")["result"]
    service.occasion=lambda text: (_ for _ in ()).throw(ValueError("Ambiguous"))
    service.evaluate(id,"alice",rev,"Unknown occasion").result(timeout=3)
    view=service.view(id,"alice")
    assert view["result"] is None and view["error"]["code"]=="OccasionClarification"


def test_guard_policy_fails_closed_without_gpu_inference():
    from app.application.outfit_review.guard import Policy
    assert Policy.resources(2*2**30,512) is None
    assert Policy.resources(2*2**30-1,512)
    assert Policy.resources(3*2**30,511)
    p=Policy()
    assert p.activity(False,0)
    p=Policy()
    assert p.activity(True,.2) is None
    assert p.activity(True,.2)
    assert Policy.jobs({"processing":1})


def test_disabled_runtime_and_busy_gpu_never_start_worker(monkeypatch):
    from app.application.outfit_review import runtime
    from app.infrastructure.ai.gpu_runtime import _GPU_LOCK
    monkeypatch.delenv("SMART_WARDROBE_OUTFIT_REVIEW_ENABLED",raising=False)
    with pytest.raises(ReviewError) as exc:runtime.QwenObserver()(None,None)
    assert exc.value.code=="Disabled"
    monkeypatch.setenv("SMART_WARDROBE_OUTFIT_REVIEW_ENABLED","true")
    with _GPU_LOCK:
        with pytest.raises(ReviewError) as exc:runtime.QwenObserver()(None,None)
    assert exc.value.code=="GpuBusy" and not runtime.LOCAL_LOCK.locked()


def test_missing_assets_release_locks_without_starting_a_model(monkeypatch,tmp_path):
    from app.application.outfit_review import runtime
    from app.infrastructure.ai.gpu_runtime import _GPU_LOCK
    monkeypatch.setenv("SMART_WARDROBE_OUTFIT_REVIEW_ENABLED","true")
    monkeypatch.setattr(runtime,"paths",lambda:(tmp_path,tmp_path/"missing.exe"))
    with pytest.raises(ReviewError) as exc:runtime.QwenObserver()(None,None)
    assert exc.value.code=="ModelUnavailable"
    assert not runtime.LOCAL_LOCK.locked() and not _GPU_LOCK.locked()


def test_guard_partial_monitor_start_cleans_owned_helpers(monkeypatch,tmp_path):
    from app.application.outfit_review import guard
    class Process:
        ended=False
        def poll(self):return 0 if self.ended else None
        def terminate(self):self.ended=True
        def wait(self,timeout):return 0
    first=Process()
    calls=[]
    def popen(*args,**kwargs):
        calls.append(1)
        if len(calls)==1:return first
        raise OSError("No activity counter helper")
    monkeypatch.setattr(guard.subprocess,"Popen",popen)
    monitor=guard.Guard(tmp_path,{"pid":123,"children":{}})
    with pytest.raises(OSError):monitor.__enter__()
    assert first.ended and monitor.stop.is_set()


def test_safety_stop_terminates_owned_worker_even_if_logs_fail(monkeypatch,tmp_path):
    from app.application.outfit_review.guard import Guard
    class Process:
        ended=False
        pid=123
        def poll(self):return None
        def terminate(self):self.ended=True
    monitor=Guard(tmp_path/"missing",{})
    process=Process();monitor.proc=process
    monitor.abort("Memory floor")
    assert process.ended and monitor.unsafe["reason"]=="Memory floor"


def test_windows_owned_job_closes_only_a_disposable_cpu_worker():
    import os,subprocess,sys
    if os.name!="nt":pytest.skip("Windows job object")
    from app.application.outfit_review.windows_job import OwnedJob
    job=OwnedJob()
    process=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],creationflags=0x08000000)
    try:
        job.attach(process.pid)
        assert process.poll() is None
        job.close()
        process.wait(timeout=5)
    finally:
        job.close()
        if process.poll() is None:process.terminate();process.wait(timeout=5)


def test_image_validation_is_serialized_and_failed_decode_releases_admission(service):
    with service.image_lock:
        with pytest.raises(ReviewError) as exc:service.create("alice",image_bytes())
    assert exc.value.code=="ImageValidationBusy"
    with pytest.raises(ReviewError):service.create("alice",b"invalid")
    assert not service.image_lock.locked()
    assert service.create("alice",image_bytes())["state"]=="uploaded"


def test_unavailable_cpu_nlp_is_not_misreported_as_an_occasion_ambiguity(service):
    from app.application.outfit_review.occasion import OccasionUnavailable
    view=analyzed(service);id=view["id"];rev=view["revision"]
    service.confirm(id,"alice",rev,True)
    service.occasion=lambda text: (_ for _ in ()).throw(OccasionUnavailable("Missing assets"))
    service.evaluate(id,"alice",rev,"Library").result(timeout=3)
    result=service.view(id,"alice")
    assert result["error"]["code"]=="SemanticUnavailable" and result["result"] is None


@pytest.mark.parametrize("finish_reason",["stop","length"])
def test_runtime_transport_and_owned_cleanup_with_explicit_test_doubles(monkeypatch,tmp_path,finish_reason):
    import threading
    from types import SimpleNamespace
    from app.application.outfit_review import runtime,guard,windows_job
    from app.application.outfit_review.images import prepare_image
    import psutil
    commands=[];attached=[]
    class Process:
        pid=12345
        ended=False
        def poll(self):return 0 if self.ended else None
        def terminate(self):self.ended=True
        def wait(self,timeout):return 0
    process=Process()
    class Job:
        closed=False
        def __enter__(self):return self
        def __exit__(self,*args):self.closed=True
        def attach(self,pid):attached.append(pid)
    job=Job()
    class Monitor:
        lock=threading.RLock()
        def __init__(self,*args,**kwargs):assert kwargs['monitor_job'] is job
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def preflight(self):return None
        def safe(self):return None
        def attach(self,p):assert p is process
    class HTTP:
        def __init__(self,value):self.value=value
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):return json.dumps(self.value).encode()
    def popen(command,**kwargs):commands.append(command);return process
    def urlopen(request,timeout):
        assert request.full_url.startswith('http://127.0.0.1:')
        return HTTP({'status':'ok'} if request.full_url.endswith('/health') else {'choices':[{'finish_reason':finish_reason,'message':{'content':json.dumps(prediction())}}]})
    monkeypatch.setattr(windows_job,'OwnedJob',lambda:job)
    monkeypatch.setattr(guard,'Guard',Monitor)
    monkeypatch.setattr(guard,'discover_backend',lambda:{})
    monkeypatch.setattr(runtime.subprocess,'Popen',popen)
    monkeypatch.setattr(runtime.urllib.request,'urlopen',urlopen)
    monkeypatch.setattr(psutil,'Process',lambda pid:SimpleNamespace(children=lambda recursive:[]))
    monkeypatch.setattr(psutil,'net_connections',lambda kind:[])
    image,png=prepare_image(image_bytes())
    call=lambda:runtime.QwenObserver()._run(image,png,tmp_path,tmp_path/'test-double.exe')
    if finish_reason=='stop':assert call().image==image
    else:
        with pytest.raises(ReviewError) as exc:call()
        assert exc.value.code=='InvalidObservation' and exc.value.raw_response
        assert exc.value.model_run['model']=='Qwen3-VL-4B-Instruct-Q4_K_M'
    assert process.ended and job.closed and attached==[process.pid]
    command=commands[0]
    assert command[command.index('--cache-ram')+1]=='0'
    assert command[command.index('--gpu-layers')+1]=='16'
    assert '--no-mmproj-offload' in command and '--fit' in command
