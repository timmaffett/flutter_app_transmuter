import pytest

from brandtool_lib import firebase_ops as fb
from fakes import FakeResource


def firebase_with_apps(apps):
    android = FakeResource(list=lambda parent: {'apps': apps})
    projects = FakeResource(androidApps=android)
    return FakeResource(projects=projects)


def test_get_android_app_found_and_missing():
    svc = firebase_with_apps([{'packageName': 'com.a', 'appId': '1:x:android:a'}])
    assert fb.get_android_app(svc, 'p', 'com.a') == '1:x:android:a'
    assert fb.get_android_app(svc, 'p', 'com.b') is None


def test_wait_for_operation_returns_on_done_and_tolerates_409():
    seq = iter([{'done': False}, {'done': True, 'response': {'ok': 1}}])
    svc = FakeResource(operations=FakeResource(get=lambda name: next(seq)))
    assert fb.wait_for_operation(svc, 'op/1', poll_seconds=0) == {'done': True, 'response': {'ok': 1}}

    svc409 = FakeResource(operations=FakeResource(
        get=lambda name: {'done': True, 'error': {'code': 409}}))
    assert 'error' in fb.wait_for_operation(svc409, 'op/2', poll_seconds=0)


def test_wait_for_operation_raises_on_real_error():
    svc = FakeResource(operations=FakeResource(
        get=lambda name: {'done': True, 'error': {'code': 500, 'message': 'x'}}))
    with pytest.raises(RuntimeError):
        fb.wait_for_operation(svc, 'op/3', poll_seconds=0)


def test_list_sha_hashes_lowercases():
    sha = FakeResource(list=lambda parent: {'certificates': [{'shaHash': 'AABB'}]})
    svc = FakeResource(projects=FakeResource(androidApps=FakeResource(sha=sha)))
    assert fb.list_sha_hashes(svc, 'p', 'app1') == {'aabb'}


def test_create_ios_app_includes_team_and_store_ids():
    captured = []

    def create(parent, body):
        captured.append(body)
        return {'name': 'op/1'}

    svc = FakeResource(
        projects=FakeResource(iosApps=FakeResource(create=create)),
        operations=FakeResource(get=lambda name: {'done': True,
                                                  'response': {'appId': '1:1:ios:x'}}))
    app_id = fb.create_ios_app(svc, 'p', 'Park-N-Go Dayton Airport Loyalty Rewards',
                               'com.d.ios',
                               team_id='TEAM123456', app_store_id='6446444444')
    assert app_id == '1:1:ios:x'
    assert captured[0]['teamId'] == 'TEAM123456'
    assert captured[0]['appStoreId'] == '6446444444'
    # same 40-char cap as the Android app - no more 20-char iOS truncation
    assert captured[0]['displayName'] == 'Park-N-Go Dayton Airport Loyalty Rewards'
    # omitted when unknown
    fb.create_ios_app(svc, 'p', 'Demo App', 'com.d.ios')
    assert 'teamId' not in captured[1] and 'appStoreId' not in captured[1]


def test_patch_ios_app_sends_update_mask():
    calls = []

    def patch(name, updateMask, body):
        calls.append((name, updateMask, body))
        return {}

    svc = FakeResource(projects=FakeResource(iosApps=FakeResource(patch=patch)))
    fb.patch_ios_app(svc, 'p', 'app1', {'teamId': 'T1', 'appStoreId': '99'})
    name, mask, body = calls[0]
    assert name == 'projects/p/iosApps/app1'
    assert mask == 'appStoreId,teamId'
    assert body == {'teamId': 'T1', 'appStoreId': '99'}


def test_get_project_number():
    crm = FakeResource(projects=FakeResource(
        get=lambda name: {'name': 'projects/123456789', 'projectId': 'p'}))
    assert fb.get_project_number(crm, 'p') == '123456789'
