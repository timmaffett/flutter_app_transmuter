//  Copyright 2026 Tim Maffett
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

/// The commented starter transmute_provisioning.yaml written by
/// `transmute provision init`. Every value marked FILL_ME must be replaced;
/// optional sections can be deleted entirely.
const String starterProvisioningYaml = r'''# transmute_provisioning.yaml
# Configuration for `transmute provision ...` - the brand cloud-provisioning
# commands (Google Cloud / Firebase / Play / App Store Connect auditing and
# creation). This file lives in the project root next to master_transmute.yaml.
#
# Requires Python 3.10+ and:
#   pip install google-api-python-client google-auth requests PyJWT cryptography pyyaml
# Google auth uses Application Default Credentials:
#   gcloud auth application-default login   (one time)

project:
  # Directory holding one sub-directory per brand.
  brands_root: FILL_ME            # e.g. brands  /  branded_loyalty
  # Per-brand values file inside each brand dir (v1 supports only this name,
  # which is also the transmuter's own per-brand contract).
  brand_config: transmute.json
  # Template directory copied when starting a new brand (optional).
  starter_brand_dir: STARTER_BRAND_DIR
  # Regex that extracts your CUSTOMER ID(s) from a brand directory name.
  # A customer id is whatever identifier YOUR server/admin system uses for the
  # brand/customer (some orgs call these "location ids"). Delete this and all
  # {customerId}/{customerIds} usages below if you have no such concept.
  # '\d+' extracts numeric ids (brand_123, brand_12_34 -> 12, 34). If a single
  # trailing id can also be TEXT (my_brand_Loyalty -> "Loyalty"), use
  # '(?<=_)\d+|[^_]+$' - every digit-run after an underscore, else the final segment.
  customer_id_pattern: '\d+'

google:
  # Project used only to bill API quota for Application Default Credentials.
  quota_project: FILL_ME
  # Billing account linked to every brand project (console.cloud.google.com/billing).
  billing_account: FILL_ME        # e.g. 012345-6789AB-CDEF01
  # Account granted owner on created brand projects (your admin login).
  admin_grantee: FILL_ME          # e.g. admin@example.com
  # Optional: service account granted editor on created projects.
  automation_service_account: ""
  # APIs that must be enabled on every brand project (audited; --fix enables).
  required_apis:
    - firebase.googleapis.com
    - firebasehosting.googleapis.com
    - maps-android-backend.googleapis.com
    - maps-ios-backend.googleapis.com
    - places-backend.googleapis.com
    - places.googleapis.com
  # App signing certificate fingerprints registered on every brand's Firebase
  # Android app and allowed on Android API keys.
  signing_certs:
    debug_sha1: "FILL:ME"
    release_sha1: "FILL:ME"
    release_sha256: "FILL:ME"
  # Optional: Google Play Developer API service-account key file (repo-root
  # relative) for the Play checks; omit to skip them.
  # play:
  #   credentials_file: play_credentials.json

# Service-account / IAM hygiene checks, audited on every brand. ON BY DEFAULT
# even when this section is absent; set `enabled: false` to opt out. Born from
# a real incident: a messaging service account had (by hand, months earlier)
# been granted project Editor - when its key leaked, the attacker used it to
# enable Compute Engine and create a probe service account. These checks catch
# every link of that chain.
security:
  # Roles the FCM messaging SA may hold; anything more is an ISSUE and the
  # audit --fix revokes the excess.
  fcm_sa_allowed_roles: [roles/firebasecloudmessaging.admin]
  # Roles no project-created service account may hold (Google-managed service
  # agents are exempt - they hold Editor by design).
  forbidden_sa_roles: [roles/owner, roles/editor]
  # Service accounts allowed to hold the forbidden roles anyway
  # (google.automation_service_account is implicitly allowed).
  privileged_sa_allowlist: []
  # Service accounts you know about beyond the messaging SA and
  # firebase-adminsdk-*; anything else in the project is flagged.
  expected_service_accounts: []
  # APIs that must NOT be enabled on brand projects (--fix disables them).
  forbidden_apis: [compute.googleapis.com]
  # Flag user-managed keys older than this many days (0 = don't check age).
  max_key_age_days: 0

# One entry per Google API key each brand needs. `field` is the key's entry in
# the brand's transmute.json; the audit verifies existence + restrictions, and
# the fixes create/adopt keys with exactly these restrictions.
api_keys:
  - field: androidGoogleMapsSDKApiKey
    label: Android Maps key                 # audit report label
    name: "Android Loyalty App Google Maps SDK API Key"   # <=63 chars
    restriction: android                    # signing certs x packageName
    services: [maps-android-backend.googleapis.com]
    match_tokens: [android, maps]           # adopt-by-name tokens
  - field: iosGoogleMapsSDKApiKey
    label: iOS Maps key
    name: "iOS Loyalty App Google Maps SDK API Key"
    restriction: ios                        # bundle-id restriction
    services: [maps-ios-backend.googleapis.com]
    match_tokens: [ios, maps]
  - field: serverGooglePlacesAPIKey
    label: Places server key
    name: "Loyalty App Google Places API Key for Server {customerIds}"
    restriction: api_only                   # API-target restriction only
    services: [places-backend.googleapis.com, places.googleapis.com]
    match_tokens: [places]
    # If the generated name can exceed Google's 63-char cap (many customer
    # ids), this prefix is dropped to make it fit.
    name_overflow_strip: "Loyalty App "
    # Optional: a server keeps its own copy of this key - fixes then print a
    # red ACTION REQUIRED banner telling the operator where to paste the new
    # key. Delete if not applicable.
    # server_copy:
    #   note: "our server uses this key"
    #   url_template: "https://admin.example.com/{customerId}/"
    #   settings_path: "Settings -> API Keys"

# Optional: where the FCM service-account JSON is configured server-side
# (shown in the FCM key fixes). Delete if not applicable.
# fcm:
#   server_copy:
#     url_template: "https://admin.example.com/{customerId}/"
#     settings_path: "Settings -> Push Notifications"

apple:
  # App ID capabilities enabled by create-apple / audited per brand.
  required_capabilities: [PUSH_NOTIFICATIONS, APPLE_ID_AUTH, ASSOCIATED_DOMAINS]
  # Repo-root directory holding backup copies of APNs auth key .p8 files.
  apns_backup_dir: appleAPNPushKey
  # Shown in ASC access-request emails and instructions.
  organization_name: FILL_ME              # e.g. Example Corp
  # Optional: full override of the built-in App Store Connect API access
  # request email template.
  # access_request_email_template: |
  #   ...
''';
