"""CPU-only activity telemetry: reliable absence versus unmeasurable state."""
import pytest
from app.application.outfit_review.guard import measured_activity,Policy


def reading():
    return dict(version='gpu-engine-activity-1.1.0',time=100.,global_counter_count=10,global_valid=True,
                requested_ids=[42],observed_gpu_pids=[7],counter_count=0,samples=[])


def test_valid_complete_inventory_allows_idle_process_without_cuda_context():
    assert measured_activity(reading(),{42},100.)==(True,0)
    policy=Policy()
    for _ in range(5):assert policy.activity(*measured_activity(reading(),{42},100.)) is None
    assert policy.quiet==5


@pytest.mark.parametrize('change',[
    {'global_valid':False},{'global_counter_count':0},{'time':96.},
    {'version':'old'},{'requested_ids':[99]}, {'observed_gpu_pids':[7,42]},
    {'counter_count':1},
])
def test_missing_stale_invalid_or_incomplete_readings_fail_closed(change):
    value=reading();value.update(change)
    assert measured_activity(value,{42},100.)==(False,0)


def test_real_activity_and_invalid_target_counter_are_not_hidden():
    value=reading();value.update(observed_gpu_pids=[7,42],counter_count=1,
        samples=[dict(instance='pid_42_luid_0_engtype_3d',status=0,percent=12.)])
    assert measured_activity(value,{42},100.)==(True,12.)
    policy=Policy()
    assert policy.activity(*measured_activity(value,{42},100.)) is None
    assert policy.activity(*measured_activity(value,{42},100.))
    value['samples'][0]['status']=999
    assert measured_activity(value,{42},100.)==(False,0)


def test_no_unrequested_process_can_supply_a_target_measurement():
    value=reading();value.update(counter_count=1,samples=[dict(instance='pid_7_luid_0_engtype_3d',status=0,percent=0.)])
    assert measured_activity(value,{42},100.)==(False,0)
