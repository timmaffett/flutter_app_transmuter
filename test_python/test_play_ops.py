from brandtool_lib import play_ops
from fakes import FakeResource


def publisher(insert_result, deleted):
    def insert(packageName, body):
        if isinstance(insert_result, Exception):
            raise insert_result
        return insert_result
    def delete(packageName, editId):
        deleted.append(editId)
        return {}
    return FakeResource(edits=FakeResource(insert=insert, delete=delete))


def test_check_app_ok_deletes_probe_edit():
    deleted = []
    status, _ = play_ops.check_app(publisher({'id': 'e1'}, deleted), 'com.a')
    assert status == play_ops.APP_OK and deleted == ['e1']


def test_check_app_missing_and_no_access():
    status, detail = play_ops.check_app(publisher(RuntimeError('HttpError 404 x'), []), 'com.a')
    assert status == play_ops.APP_MISSING and 'com.a' in detail
    status, _ = play_ops.check_app(publisher(RuntimeError('HttpError 403 y'), []), 'com.a')
    assert status == play_ops.NO_ACCESS
