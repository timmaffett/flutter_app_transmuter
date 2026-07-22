import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from brandtool_lib import asc_api


def make_p8(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    p = tmp_path / 'AuthKey_TESTKEY123.p8'
    p.write_bytes(pem)
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return str(p), pub_pem


class FakeResponse:
    def __init__(self, status_code, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = b'x' if payload is not None else b''

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def client_with(tmp_path, responses):
    p8, _ = make_p8(tmp_path)
    return asc_api.AscClient('TESTKEY123', 'issuer-uuid', p8,
                             session=FakeSession(responses), sleep=lambda s: None)


def test_token_is_valid_es256_jwt(tmp_path):
    p8, pub_pem = make_p8(tmp_path)
    client = asc_api.AscClient('TESTKEY123', 'my-issuer', p8)
    token = client._token()
    header = pyjwt.get_unverified_header(token)
    assert header['kid'] == 'TESTKEY123' and header['alg'] == 'ES256'
    payload = pyjwt.decode(token, pub_pem, algorithms=['ES256'],
                           audience='appstoreconnect-v1')
    assert payload['iss'] == 'my-issuer'
    assert payload['exp'] - payload['iat'] == 19 * 60
    assert client._token() == token  # cached


def test_get_merges_pagination(tmp_path):
    client = client_with(tmp_path, [
        FakeResponse(200, {'data': [{'id': '1'}],
                           'links': {'next': asc_api.BASE_URL + '/apps?cursor=x'}}),
        FakeResponse(200, {'data': [{'id': '2'}], 'links': {}}),
    ])
    assert client.get('/apps') == [{'id': '1'}, {'id': '2'}]


def test_429_backs_off_then_succeeds(tmp_path):
    client = client_with(tmp_path, [
        FakeResponse(429, {'errors': []}),
        FakeResponse(200, {'data': []}),
    ])
    assert client.get('/apps') == []


def test_error_mapping(tmp_path):
    with pytest.raises(asc_api.AscAuthError):
        client_with(tmp_path, [FakeResponse(401, {'errors': [{'detail': 'bad key'}]})]).get('/apps')
    with pytest.raises(asc_api.AscPermissionError):
        client_with(tmp_path, [FakeResponse(403, {'errors': [{'detail': 'role'}]})]).get('/apps')
    with pytest.raises(asc_api.AscApiError):
        client_with(tmp_path, [FakeResponse(500, None, 'boom')]).get('/apps')


def test_post_returns_body_and_single_resource_get(tmp_path):
    client = client_with(tmp_path, [FakeResponse(201, {'data': {'id': 'new'}})])
    assert client.post('/bundleIds', {'data': {}}) == {'data': {'id': 'new'}}
    client2 = client_with(tmp_path, [FakeResponse(200, {'data': {'id': 'single'}})])
    assert client2.get('/apps/xyz') == {'data': {'id': 'single'}}
