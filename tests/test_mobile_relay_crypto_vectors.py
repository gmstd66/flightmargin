import json
from pathlib import Path

from relay.credentials import (
    credential_digest,
    normalize_manual_code,
    pairing_manual_digest,
    pairing_qr_digest,
    parse_credential,
    parse_pairing_token,
)


VECTOR_PATH = Path(__file__).parent / "fixtures" / "mobile-relay-crypto-vectors.json"


def test_shared_mobile_relay_hmac_vectors_match_python_reference():
    vectors = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    pepper = vectors["pepper"].encode("utf-8")

    assert credential_digest(
        parse_credential(vectors["host_credential"], "host"), pepper
    ) == vectors["host_digest"]
    assert credential_digest(
        parse_credential(vectors["device_credential"], "device"), pepper
    ) == vectors["device_digest"]
    assert pairing_qr_digest(
        parse_pairing_token(vectors["pairing_token"]), pepper
    ) == vectors["pairing_qr_digest"]
    assert pairing_manual_digest(
        normalize_manual_code(vectors["manual_code"]), pepper
    ) == vectors["pairing_manual_digest"]
