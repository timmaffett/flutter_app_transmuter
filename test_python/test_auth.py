import pytest

from brandtool_lib import auth


def test_missing_service_account_file_raises():
    with pytest.raises(FileNotFoundError):
        auth.build_credentials(creds_file='nonexistent-file.json')


def test_scopes_constants():
    assert auth.CLOUD_PLATFORM == 'https://www.googleapis.com/auth/cloud-platform'
    assert auth.PUBLISHER_SCOPE == 'https://www.googleapis.com/auth/androidpublisher'


def test_missing_adc_prints_setup_walkthrough(monkeypatch):
    # A user without gcloud/ADC (real field report) got a raw
    # DefaultCredentialsError traceback - it must be a guided SystemExit.
    import google.auth
    from google.auth import exceptions

    def no_adc(scopes=None):
        raise exceptions.DefaultCredentialsError('Your default credentials were not found.')

    monkeypatch.setattr(google.auth, 'default', no_adc)
    with pytest.raises(SystemExit) as e:
        auth.build_credentials(admin_hint='admin@example.com')
    msg = str(e.value)
    assert 'gcloud auth application-default login' in msg
    assert 'winget install Google.CloudSDK' in msg
    assert 'brew install --cask google-cloud-sdk' in msg
    assert 'NEW terminal' in msg
    assert 'admin@example.com' in msg
    assert '--creds' in msg
