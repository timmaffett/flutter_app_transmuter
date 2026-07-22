"""Credential and Google API client construction for brandtool."""
from google.oauth2 import service_account
from googleapiclient import discovery

CLOUD_PLATFORM = 'https://www.googleapis.com/auth/cloud-platform'
PUBLISHER_SCOPE = 'https://www.googleapis.com/auth/androidpublisher'


def _adc_setup_walkthrough(admin_hint=None):
    who = (f'your organization Google admin account ({admin_hint})' if admin_hint
           else 'your organization Google admin account')
    return f'''
NO GOOGLE CREDENTIALS FOUND (Application Default Credentials are not set up).

The provisioning commands authenticate with ADC. One-time setup:

  1. Install the Google Cloud CLI (gcloud) if you do not have it:
       Windows:  winget install Google.CloudSDK
                 (or the installer: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe)
       macOS:    brew install --cask google-cloud-sdk
       Linux:    https://cloud.google.com/sdk/docs/install
  2. Open a NEW terminal (the installer updates PATH), then run:
       gcloud auth application-default login
     Sign in as {who}.
  3. Re-run this command.

(Alternative: pass --creds <service-account.json> to use a service-account key
instead of ADC.)'''


def build_credentials(creds_file=None, quota_project=None, scopes=None,
                      admin_hint=None):
    """ADC by default (gcloud auth application-default login); SA file when creds_file given.

    quota_project pins API quota/billing for the calls to a project that has the
    relevant APIs enabled (avoids SERVICE_DISABLED 403s on the ADC default quota project).
    Missing ADC exits with a full setup walkthrough (gcloud install + login)
    instead of a traceback; admin_hint names the account to sign in as."""
    scopes = scopes or [CLOUD_PLATFORM]
    if creds_file:
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=scopes)
    else:
        import google.auth
        from google.auth import exceptions as _gexc
        try:
            creds, _ = google.auth.default(scopes=scopes)
        except _gexc.DefaultCredentialsError:
            raise SystemExit(_adc_setup_walkthrough(admin_hint))
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
