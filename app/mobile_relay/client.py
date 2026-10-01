"""Bounded standard-library transport for the FlightMargin relay v1 API."""

from __future__ import annotations

import json
import ssl
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

from app.mobile_relay.config import validate_endpoint
from app.mobile_relay.identity import HostIdentity


class RelayClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RelayClientError("Relay request was redirected", status_code=code)


class RelayClient:
    def __init__(self, endpoint: str, *, timeout: float = 5.0, opener=None):
        self.endpoint = validate_endpoint(endpoint)
        self.timeout = timeout
        self.opener = opener or build_opener(
            _RejectRedirects(), HTTPSHandler(context=ssl.create_default_context())
        )

    def _request(self, method: str, path: str, payload: dict, credential=None) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if credential is not None:
            headers["Authorization"] = f"Bearer {credential}"
        request = Request(
            f"{self.endpoint}{path}",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read(65537)
                if len(body) > 65536:
                    raise RelayClientError("Relay returned an invalid response")
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise ValueError
                return result
        except RelayClientError:
            raise
        except HTTPError as exc:
            raise RelayClientError(
                "Relay request was rejected", status_code=exc.code
            ) from None
        except (URLError, TimeoutError, OSError):
            raise RelayClientError("Relay is unavailable") from None
        except (ValueError, json.JSONDecodeError):
            raise RelayClientError("Relay returned an invalid response") from None

    def register_host(
        self, identity: HostIdentity, *, display_name: str, platform_name: str, app_version: str
    ) -> dict:
        result = self._request(
            "POST",
            "/v1/hosts/register",
            {
                "host_id": identity.host_id,
                "display_name": display_name,
                "platform": platform_name,
                "app_version": app_version,
                "credential": identity.credential,
            },
        )
        if result.get("host_id") != identity.host_id or result.get("result") not in {
            "registered",
            "already_registered",
        }:
            raise RelayClientError("Relay returned an invalid response")
        return result

    def upload_quota(self, credential: str, payload: dict) -> dict:
        result = self._request("PUT", "/v1/quota", payload, credential)
        if result.get("result") not in {"accepted", "stale"}:
            raise RelayClientError("Relay returned an invalid response")
        return result

    def create_pairing(self, credential: str) -> dict:
        result = self._request("POST", "/v1/pairings", {}, credential)
        required = ("pairing_token", "manual_code", "expires_at", "deep_link")
        if not all(isinstance(result.get(key), str) and result[key] for key in required):
            raise RelayClientError("Relay returned an invalid response")
        token = result["pairing_token"]
        try:
            expiration = datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))
        except ValueError:
            raise RelayClientError("Relay returned an invalid response") from None
        if (
            expiration.utcoffset() is None
            or not token.startswith("fmp1.")
            or result["deep_link"] != f"flightmargin://pair/v1?token={token}"
        ):
            raise RelayClientError("Relay returned an invalid response")
        return {key: result[key] for key in required}
