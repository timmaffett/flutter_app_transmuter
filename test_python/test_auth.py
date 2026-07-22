import pytest

from brandtool_lib import auth


def test_missing_service_account_file_raises():
    with pytest.raises(FileNotFoundError):
        auth.build_credentials(creds_file='nonexistent-file.json')


def test_scopes_constants():
    assert auth.CLOUD_PLATFORM == 'https://www.googleapis.com/auth/cloud-platform'
    assert auth.PUBLISHER_SCOPE == 'https://www.googleapis.com/auth/androidpublisher'
