"""Credential and Google API client construction for brandtool."""
from google.oauth2 import service_account
from googleapiclient import discovery

CLOUD_PLATFORM = 'https://www.googleapis.com/auth/cloud-platform'
PUBLISHER_SCOPE = 'https://www.googleapis.com/auth/androidpublisher'


def build_credentials(creds_file=None, quota_project=None, scopes=None):
    """ADC by default (gcloud auth application-default login); SA file when creds_file given.

    quota_project pins API quota/billing for the calls to a project that has the
    relevant APIs enabled (avoids SERVICE_DISABLED 403s on the ADC default quota project).
    """
    scopes = scopes or [CLOUD_PLATFORM]
    if creds_file:
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=scopes)
    else:
        import google.auth
        creds, _ = google.auth.default(scopes=scopes)
    if quota_project:
        creds = creds.with_quota_project(quota_project)
    return creds


def build_service(name, version, creds):
    return discovery.build(name, version, credentials=creds, cache_discovery=False)


def build_services(creds):
    """The standard client set used by audit/create commands."""
    return {
        'crm': build_service('cloudresourcemanager', 'v3', creds),
        'usage': build_service('serviceusage', 'v1', creds),
        'firebase': build_service('firebase', 'v1beta1', creds),
        'apikeys': build_service('apikeys', 'v2', creds),
        'iam': build_service('iam', 'v1', creds),
        'billing': build_service('cloudbilling', 'v1', creds),
    }
