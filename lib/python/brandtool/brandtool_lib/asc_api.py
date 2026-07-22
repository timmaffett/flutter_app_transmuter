"""App Store Connect API transport: Team-Key JWT auth + REST helpers. No business logic."""
import time

import jwt
import requests

BASE_URL = 'https://api.appstoreconnect.apple.com/v1'


class AscError(RuntimeError):
    pass


class AscAuthError(AscError):
    pass


class AscPermissionError(AscError):
    pass


class AscApiError(AscError):
    pass


# Apple error text that only the team's Account Holder can resolve (pending
# agreements, membership expiry/suspension). There is no status endpoint;
# these arrive as 403s on ordinary API calls.
_ACCOUNT_HOLDER_SIGNALS = ('agreement', 'membership', 'expired', 'suspend',
                           'renew', 'terms')


def needs_account_holder(message):
    m = message.lower()
    return any(s in m for s in _ACCOUNT_HOLDER_SIGNALS)


def perm_error_message(detail):
    if needs_account_holder(detail):
        return f'Apple account blocked pending Account Holder action (403): {detail}'
    return f'API key role is insufficient (403): {detail}'


class AscClient:
    """Authenticated client for one team's App Store Connect API Team Key."""

    def __init__(self, key_id, issuer_id, p8_path, session=None, sleep=time.sleep):
        self.key_id = key_id
        self.issuer_id = issuer_id
        with open(p8_path) as f:
            self._private_key = f.read()
        self._session = session or requests.Session()
        self._sleep = sleep
        self._token_value = None
        self._token_expiry = 0

    def _token(self):
        now = int(time.time())
        if not self._token_value or now > self._token_expiry - 60:
            self._token_expiry = now + 19 * 60
            self._token_value = jwt.encode(
                {'iss': self.issuer_id, 'iat': now, 'exp': self._token_expiry,
                 'aud': 'appstoreconnect-v1'},
                self._private_key, algorithm='ES256',
                headers={'kid': self.key_id, 'typ': 'JWT'})
        return self._token_value

    def _request(self, method, path, params=None, body=None):
        url = path if path.startswith('http') else BASE_URL + path
        resp = None
        for backoff in (2, 8, 32, None):
            resp = self._session.request(
                method, url, params=params, json=body,
                headers={'Authorization': f'Bearer {self._token()}'})
            if resp.status_code == 429 and backoff is not None:
                self._sleep(backoff)
                continue
            break
        if resp.status_code == 401:
            raise AscAuthError(f'App Store Connect rejected the API key (401): {_detail(resp)}')
        if resp.status_code == 403:
            raise AscPermissionError(perm_error_message(_detail(resp)))
        if resp.status_code >= 400:
            raise AscApiError(f'App Store Connect API error {resp.status_code}: {_detail(resp)}')
        if not resp.content:
            return {}
        return resp.json()

    def get(self, path, params=None):
        """GET; list responses follow links.next pagination and return the merged data list."""
        result = self._request('GET', path, params=params)
        if not isinstance(result.get('data'), list):
            return result
        data = list(result['data'])
        while result.get('links', {}).get('next'):
            result = self._request('GET', result['links']['next'])
            data.extend(result.get('data', []))
        return data

    def post(self, path, body):
        return self._request('POST', path, body=body)

    def patch(self, path, body):
        return self._request('PATCH', path, body=body)


def _detail(resp):
    try:
        errs = resp.json().get('errors', [])
        parts = []
        for e in errs:
            code = e.get('code', '')
            text = e.get('detail') or e.get('title', '')
            parts.append(f'{code}: {text}' if code else text)
        return '; '.join(p for p in parts if p) or resp.text[:200]
    except Exception:
        return resp.text[:200]
