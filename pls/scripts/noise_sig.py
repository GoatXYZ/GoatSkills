"""NOISE-SIG-1 request signatures for the bot's private sidecar APIs.

A signed request carries five headers: a key id `<service>.<cap>.<n>`, a Unix
timestamp, a random nonce, the SHA-256 of the exact body and an HMAC-SHA256
over a nine-line canonical string that also names the verifier's own service
(the audience). Key `.0` of each capability is the service's existing secret,
used only as a bootstrap signing key, never as a bearer; keys `n >= 1` come
from a key file. The wire format and the conformance vectors below are shared
with `bot.core.service-auth`; both refuse to start when a vector fails.

Stdlib only: the aiohttp glue lives in `common.py`.
"""

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import stat
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field


SCHEME = "NOISE-SIG-1"
SIGNATURE_PREFIX = "noise1="
H_KEY, H_TIMESTAMP, H_NONCE, H_DIGEST, H_SIGNATURE = (
    "X-Noise-Key", "X-Noise-Timestamp", "X-Noise-Nonce",
    "X-Noise-Content-SHA256", "X-Noise-Signature")
SIGNED_HEADERS = (H_KEY, H_TIMESTAMP, H_NONCE, H_DIGEST, H_SIGNATURE)
EMPTY_SHA256 = "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU"
AUDIENCES = frozenset({"dispatch", "cloak-direct", "retrieval", "mail", "news",
                       "chain", "signal-notify", "core-browser", "pls", "lounge-chain"})
SKEW_SECONDS = 60
# The skew check accepts a 121-second inclusive window of whole seconds, so a
# nonce must outlive it or a request stamped +60 s replays once purged.
NONCE_TTL_SECONDS = 2 * SKEW_SECONDS + 2
NONCE_CAPACITY = 65536
LOG_INTERVAL_SECONDS = 60

KID_RE = re.compile(r"[a-z][a-z0-9-]{0,31}\.[a-z][a-z0-9-]{0,31}\.(0|[1-9][0-9]{0,5})")
CAP_RE = re.compile(r"[a-z][a-z0-9-]{0,31}")
TIMESTAMP_RE = re.compile(r"[0-9]{10}")
NONCE_RE = re.compile(r"[A-Za-z0-9_-]{22}")
DIGEST_RE = re.compile(r"[A-Za-z0-9_-]{43}")
SIGNATURE_RE = re.compile(r"noise1=[A-Za-z0-9_-]{43}")
KEY_RE = re.compile(r"[A-Za-z0-9_-]{43,256}")
TARGET_RE = re.compile(r"[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]*")

MESSAGES = {
    "auth-missing": "Request signature is missing.",
    "auth-invalid": "Request signature is invalid.",
    "auth-unknown-key": "Request key is not accepted.",
    "auth-stale": "Request timestamp is outside the accepted window.",
    "auth-replayed": "Request was already used.",
    "forbidden": "Forbidden.",
    "auth-replay-cache-full": "Replay protection is full; retry later.",
    "content-digest-mismatch": "Request body does not match its signed digest.",
}
STATUSES = {
    "auth-missing": 401, "auth-invalid": 401, "auth-unknown-key": 401,
    "auth-stale": 401, "auth-replayed": 401, "forbidden": 403,
    "auth-replay-cache-full": 503, "content-digest-mismatch": 400,
}


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def content_sha256(data: bytes) -> str:
    return b64url(hashlib.sha256(data or b"").digest())


def media_type(value: str | None) -> str:
    """The Content-Type media type: cut at `;`, strip spaces and tabs, ASCII lowercase."""
    if value is None:
        return ""
    media = value.split(";", 1)[0].strip(" \t")
    return media.translate(_ASCII_LOWER)


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def canonical_string(audience, kid, method, target, timestamp, nonce, content_type, digest) -> str:
    return "\n".join((SCHEME, audience, kid, method, target, str(timestamp), nonce,
                      content_type, digest))


def compute_mac(key: str, canonical: str) -> str:
    return b64url(hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest())


def sign_headers(key: str, audience: str, kid: str, method: str, target: str,
                 body: bytes = b"", content_type: str | None = None, *,
                 timestamp: int | None = None, nonce: str | None = None) -> dict[str, str]:
    """Headers for one signed request. Sign afresh for every attempt."""
    target = target or "/"
    if not TARGET_RE.fullmatch(target):
        raise ValueError("Signed request targets must be percent-encoded.")
    timestamp = str(int(time.time()) if timestamp is None else timestamp)
    nonce = nonce if nonce is not None else b64url(secrets.token_bytes(16))
    digest = content_sha256(body)
    canonical = canonical_string(audience, kid, method, target, timestamp, nonce,
                                 media_type(content_type), digest)
    return {
        H_KEY: kid,
        H_TIMESTAMP: timestamp,
        H_NONCE: nonce,
        H_DIGEST: digest,
        H_SIGNATURE: SIGNATURE_PREFIX + compute_mac(key, canonical),
    }


# Conformance vectors shared with bot.core.service-auth (spec section 2).
_VECTOR_KEY = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
_VECTORS = (
    {
        "audience": "retrieval", "kid": "retrieval.data.1", "method": "POST",
        "target": "/search?collection=help%3Adocs&k=6", "timestamp": 1760812345,
        "nonce": "Xq3v0b7ZkqI1o9mR2c8T1w",
        "content_type": "application/json; charset=utf-8",
        "body": '{"query":"noise","topK":6}'.encode("utf-8"),
        "canonical": "NOISE-SIG-1\nretrieval\nretrieval.data.1\nPOST\n"
                     "/search?collection=help%3Adocs&k=6\n1760812345\n"
                     "Xq3v0b7ZkqI1o9mR2c8T1w\napplication/json\n"
                     "0p5VkGFUSXOBIxDAbhZI9Xa0F1oIWMoI8UwlIWVfkaQ",
        "canonical_sha256": "50558dcd81788c4865605bf155f581b8a0f0e3640ada1c9b5eac8cdea959af5f",
        "digest": "0p5VkGFUSXOBIxDAbhZI9Xa0F1oIWMoI8UwlIWVfkaQ",
        "mac": "-Zn7J3eUFaicshF07Fovcj12UdTkHUxksaZhp8TdA6M",
    },
    {
        "audience": "mail", "kid": "mail.data.1", "method": "GET",
        "target": "/v1/messages?after=0&limit=50", "timestamp": 1760812345,
        "nonce": "AAAAAAAAAAAAAAAAAAAAAA", "content_type": None, "body": b"",
        "canonical": "NOISE-SIG-1\nmail\nmail.data.1\nGET\n/v1/messages?after=0&limit=50\n"
                     "1760812345\nAAAAAAAAAAAAAAAAAAAAAA\n\n"
                     "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU",
        "canonical_sha256": None,
        "digest": EMPTY_SHA256,
        "mac": "yq8dFcs-GAcjg1oCEp0BqYndm8ytuWHXnkDutkQfoMk",
    },
)


def self_check() -> None:
    """Run the real signing path on both vectors; RuntimeError on any mismatch."""
    for index, vector in enumerate(_VECTORS):
        name = "AB"[index]
        headers = sign_headers(_VECTOR_KEY, vector["audience"], vector["kid"], vector["method"],
                               vector["target"], vector["body"], vector["content_type"],
                               timestamp=vector["timestamp"], nonce=vector["nonce"])
        canonical = canonical_string(vector["audience"], headers[H_KEY], vector["method"],
                                     vector["target"], headers[H_TIMESTAMP], headers[H_NONCE],
                                     media_type(vector["content_type"]), headers[H_DIGEST])
        problems = []
        if canonical != vector["canonical"]:
            problems.append("canonical string")
        if (vector["canonical_sha256"]
                and hashlib.sha256(canonical.encode("utf-8")).hexdigest() != vector["canonical_sha256"]):
            problems.append("canonical digest")
        if headers[H_DIGEST] != vector["digest"]:
            problems.append("content digest")
        if headers[H_SIGNATURE] != SIGNATURE_PREFIX + vector["mac"]:
            problems.append("MAC")
        if problems:
            raise RuntimeError(f"{SCHEME} self-check vector {name} failed: {', '.join(problems)}.")


def _header_values(headers, name):
    getall = getattr(headers, "getall", None)
    if callable(getall):
        return list(getall(name, []))
    value = headers.get(name)
    return [] if value is None else [value]


def _kid_cap(kid):
    return kid.split(".")[1]


def _kid_number(kid):
    return int(kid.rsplit(".", 1)[1])


def load_key_file(path: str, service: str, caps) -> dict[str, str]:
    """Signing keys `n >= 1` from a `kid key` file; a missing file has none."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        return {}
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        mode = os.fstat(handle.fileno()).st_mode
        if not stat.S_ISREG(mode):
            raise ValueError(f"Key file {path} is not a regular file.")
        if mode & 0o077:
            raise ValueError(f"Key file {path} must not be readable or writable by group or others.")
        keys = {}
        for number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            parts = text.split()
            if len(parts) != 2:
                raise ValueError(f"Key file {path} line {number}: expected a key id and a key.")
            kid, key = parts
            if not KID_RE.fullmatch(kid) or not kid.startswith(f"{service}."):
                raise ValueError(f"Key file {path} line {number}: the key id is not a {service} key id.")
            if _kid_cap(kid) not in caps:
                raise ValueError(f"Key file {path} line {number}: the key id names an unknown capability.")
            if _kid_number(kid) < 1:
                raise ValueError(f"Key file {path} line {number}: key number 0 is the bootstrap secret.")
            if not KEY_RE.fullmatch(key):
                raise ValueError(f"Key file {path} line {number}: the key must be 43 to 256 base64url characters.")
            if kid in keys:
                raise ValueError(f"Key file {path} line {number}: duplicate key id.")
            keys[kid] = key
        return keys


def server_time() -> int:
    return int(time.time())


class AuthFailure(Exception):
    """An authentication or authorization refusal; shaped like common.SidecarError."""

    def __init__(self, error_code, retry_after=None):
        super().__init__(MESSAGES[error_code])
        self.status_code = STATUSES[error_code]
        self.error_code = error_code
        self.reason = error_code
        self.retry_after = retry_after


@dataclass(frozen=True)
class Principal:
    kid: str
    capability: str
    content_sha256: str               # signed digest
    nonce: str = field(repr=False)    # replay key
    body_present: bool = False        # signed body still to be digest-checked


class BodyDigest:
    """Hash a body as it streams in and compare it with the signed digest at EOF."""

    def __init__(self, expected: str):
        self._expected = expected
        self._hash = hashlib.sha256()

    def update(self, chunk: bytes) -> None:
        self._hash.update(chunk)

    def verify(self) -> None:
        if not hmac.compare_digest(b64url(self._hash.digest()), self._expected):
            raise AuthFailure("content-digest-mismatch")


class _NonceCache:
    """Bounded replay cache; never evicts a live entry."""

    def __init__(self, capacity, ttl, monotonic):
        self.capacity = capacity
        self.ttl = ttl
        self.monotonic = monotonic
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def _purge(self, now):
        # A fixed lifetime keeps insertion order equal to expiry order.
        while self.entries:
            key, expires = next(iter(self.entries.items()))
            if expires > now:
                break
            del self.entries[key]

    def insert(self, kid, nonce):
        with self.lock:
            now = self.monotonic()
            self._purge(now)
            key = (kid, nonce)
            if key in self.entries:
                raise AuthFailure("auth-replayed")
            if len(self.entries) >= self.capacity:
                raise AuthFailure("auth-replay-cache-full", retry_after=1)
            self.entries[key] = now + self.ttl

    def __len__(self):
        with self.lock:
            self._purge(self.monotonic())
            return len(self.entries)


class Verifier:
    """One service's keyring, verification order, replay cache and counters."""

    def __init__(self, service: str, prefix: str, caps: tuple[str, ...], *,
                 bootstrap_keys: dict[str, str] | None = None,
                 keys_file: str | None = None,
                 environ=os.environ, clock=time.time, monotonic=time.monotonic,
                 logger=None, extra_status: dict | None = None):
        self_check()
        if service not in AUDIENCES:
            raise ValueError(f"Unknown {SCHEME} service {service!r}.")
        caps = tuple(caps)
        if not caps or not all(isinstance(cap, str) and CAP_RE.fullmatch(cap) for cap in caps):
            raise ValueError(f"{service} capabilities must be lowercase names.")
        keys = {}
        for cap, secret in (bootstrap_keys or {}).items():
            if cap not in caps:
                raise ValueError(f"{service} bootstrap key names an unknown capability.")
            if not isinstance(secret, str) or not secret:
                raise ValueError(f"{service} bootstrap {cap} secret is missing.")
            keys[f"{service}.{cap}.0"] = secret
        path = keys_file or environ.get(f"{prefix}_KEYS_FILE") or f"/etc/noise/{service}.keys"
        keys.update(load_key_file(path, service, caps))
        for kid in keys:
            if not KID_RE.fullmatch(kid) or not kid.startswith(f"{service}."):
                raise ValueError(f"{service} key ids must be well formed.")
        for cap in caps:
            if not any(_kid_cap(kid) == cap for kid in keys):
                raise ValueError(f"{service} has no key for capability {cap}.")
        owners = {}
        for kid, key in keys.items():
            fingerprint = hashlib.sha256(key.encode("utf-8")).digest()
            owner = owners.setdefault(fingerprint, _kid_cap(kid))
            if owner != _kid_cap(kid):
                raise ValueError(f"{service} capabilities must not share a key.")
        self.service = service
        self.prefix = prefix
        self.caps = caps
        self.keys = keys
        self.clock = clock
        self.logger = logger or logging.getLogger("noise.auth")
        self.extra_status = dict(extra_status or {})
        self.nonces = _NonceCache(NONCE_CAPACITY, NONCE_TTL_SECONDS, monotonic)
        self.monotonic = monotonic
        self.successes = {}
        self.failures = {}
        self.log_state = {}
        self.counter_lock = threading.Lock()
        self.boot_second = int(clock())

    # -- counters -------------------------------------------------------------

    def _kid_label(self, kid):
        if not kid:
            return "-"
        return kid if kid in self.keys else "unknown"

    def record(self, kid: str, reason: str | None = None, peer: str | None = None) -> None:
        label = self._kid_label(kid)
        with self.counter_lock:
            if reason is None:
                by_kid = self.successes.setdefault("sig", {})
                by_kid[label] = by_kid.get(label, 0) + 1
                return
            by_kid = self.failures.setdefault(reason, {})
            by_kid[label] = by_kid.get(label, 0) + 1
            now = self.monotonic()
            last, suppressed = self.log_state.get(reason, (None, 0))
            if last is not None and now - last < LOG_INTERVAL_SECONDS:
                self.log_state[reason] = (last, suppressed + 1)
                return
            self.log_state[reason] = (now, 0)
        self.logger.warning("auth failure service=%s reason=%s kid=%s peer=%s suppressed=%d",
                            self.service, reason, label, peer or "-", suppressed)

    def _fail(self, kid, error_code, peer, retry_after=None):
        self.record(kid, error_code, peer)
        return AuthFailure(error_code, retry_after)

    # -- verification ---------------------------------------------------------

    def authenticate(self, method: str, target: str, headers, *,
                     body_present: bool, peer: str | None = None) -> Principal:
        """NOISE-SIG-1 from headers alone. Any other credential, such as a
        bearer token, is no credential: 401 auth-missing."""
        values = {name: _header_values(headers, name) for name in SIGNED_HEADERS}
        sent_kid = values[H_KEY][0] if len(values[H_KEY]) == 1 else None
        if any(not found for found in values.values()):
            raise self._fail(sent_kid, "auth-missing", peer)
        content_types = _header_values(headers, "Content-Type")
        if any(len(found) > 1 for found in values.values()) or len(content_types) > 1:
            raise self._fail(sent_kid, "auth-invalid", peer)
        kid, timestamp, nonce, digest, signature = (values[name][0] for name in SIGNED_HEADERS)
        if not (KID_RE.fullmatch(kid) and TIMESTAMP_RE.fullmatch(timestamp)
                and NONCE_RE.fullmatch(nonce) and DIGEST_RE.fullmatch(digest)
                and SIGNATURE_RE.fullmatch(signature)):
            raise self._fail(kid, "auth-invalid", peer)
        key = self.keys.get(kid) if kid.startswith(f"{self.service}.") else None
        if key is None:
            raise self._fail(kid, "auth-unknown-key", peer)
        ts = int(timestamp)
        if abs(int(self.clock()) - ts) > SKEW_SECONDS or ts <= self.boot_second:
            raise self._fail(kid, "auth-stale", peer)
        canonical = canonical_string(self.service, kid, method, target, timestamp, nonce,
                                     media_type(content_types[0] if content_types else None),
                                     digest)
        expected = SIGNATURE_PREFIX + compute_mac(key, canonical)
        if not hmac.compare_digest(signature.encode("ascii"), expected.encode("ascii")):
            raise self._fail(kid, "auth-invalid", peer)
        if not body_present and not hmac.compare_digest(digest, EMPTY_SHA256):
            raise self._fail(kid, "content-digest-mismatch", peer)
        return Principal(kid, _kid_cap(kid), digest, nonce, body_present)

    def authorize(self, principal: Principal, capability: str | None) -> None:
        wanted = principal.capability if capability is None else capability
        if principal.capability != wanted or principal.capability not in self.caps:
            raise self._fail(principal.kid, "forbidden", None)
        try:
            self.nonces.insert(principal.kid, principal.nonce)
        except AuthFailure as failure:
            self.record(principal.kid, failure.reason)
            raise
        if principal.body_present:
            return   # counted by verify_body once the digest checks out
        self.record(principal.kid)

    def body_digest(self, principal: Principal) -> BodyDigest | None:
        if not principal.body_present:
            return None
        return BodyDigest(principal.content_sha256)

    def verify_body(self, principal: Principal, digest: BodyDigest,
                    peer: str | None = None) -> None:
        """Check a signed body at EOF and count the request's auth outcome."""
        try:
            digest.verify()
        except AuthFailure as failure:
            self.record(principal.kid, failure.reason, peer)
            raise
        self.record(principal.kid)

    def status(self) -> dict:
        with self.counter_lock:
            successes = {scheme: dict(by_kid) for scheme, by_kid in self.successes.items()}
            failures = {reason: dict(by_kid) for reason, by_kid in self.failures.items()}
        result = {
            "ok": True,
            "service": self.service,
            "scheme": SCHEME,
            "keys": sorted(self.keys),
            "successes": successes,
            "failures": failures,
            "nonceCache": {"entries": len(self.nonces), "capacity": self.nonces.capacity},
            "bootTime": self.boot_second,
            "serverTime": int(self.clock()),
        }
        result.update(self.extra_status)
        return result


if __name__ == "__main__":
    self_check()
    print(f"{SCHEME} self-check passed.")
