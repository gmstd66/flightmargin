"""Separate FastAPI application for the FlightMargin mobile relay."""

import base64
import secrets
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status

from relay.config import RelayConfig
from relay.credentials import (
    CREDENTIAL_MAX_LENGTH,
    InvalidCredential,
    normalize_manual_code,
    pairing_manual_digest,
    pairing_qr_digest,
    parse_credential,
    parse_pairing_token,
)
from relay.database import (
    AuthenticationFailed,
    PairingCodeCollision,
    PairingFailed,
    RegistrationConflict,
    RelayDatabase,
)
from relay.models import HostRegistration, PairingClaim, QuotaReport


AUTHENTICATION_ERROR = "Invalid or revoked credential"
PAIRING_ERROR = "Pairing could not be completed"
MANUAL_CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _bearer_credential(authorization: str | None, kind: str):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTHENTICATION_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:]
    if not token or len(token) > CREDENTIAL_MAX_LENGTH or " " in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTHENTICATION_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return parse_credential(token, kind)
    except InvalidCredential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTHENTICATION_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def create_app(config: RelayConfig | None = None) -> FastAPI:
    application = FastAPI(title="FlightMargin Relay", version="1")

    def database() -> RelayDatabase:
        return RelayDatabase(config or RelayConfig.from_environment())

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.post("/v1/hosts/register", status_code=status.HTTP_201_CREATED)
    def register_host(
        registration: HostRegistration,
        db: RelayDatabase = Depends(database),
    ) -> dict:
        try:
            credential = parse_credential(registration.credential, "host")
        except InvalidCredential:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Malformed host credential",
            ) from None
        try:
            created = db.register_host(registration, credential)
        except RegistrationConflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Host or credential identifier is already registered",
            ) from None
        return {
            "api_version": 1,
            "registered": created,
            "result": "registered" if created else "already_registered",
            "host_id": registration.host_id,
        }

    @application.put("/v1/quota")
    def put_quota(
        report: QuotaReport,
        authorization: str | None = Header(default=None),
        db: RelayDatabase = Depends(database),
    ) -> dict:
        credential = _bearer_credential(authorization, "host")
        try:
            accepted = db.put_quota(credential, report)
        except AuthenticationFailed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTHENTICATION_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        return {
            "result": "accepted" if accepted else "stale",
            "sampled_at": report.sampled_at,
        }

    @application.post("/v1/pairings", status_code=status.HTTP_201_CREATED)
    def create_pairing(
        authorization: str | None = Header(default=None),
        db: RelayDatabase = Depends(database),
    ) -> dict:
        credential = _bearer_credential(authorization, "host")
        for _ in range(5):
            session_id = uuid4()
            qr_secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(
                b"="
            ).decode("ascii")
            pairing_token = f"fmp1.{session_id}.{qr_secret}"
            parsed_token = parse_pairing_token(pairing_token)
            normalized_manual_code = "".join(
                secrets.choice(MANUAL_CODE_ALPHABET) for _ in range(10)
            )
            manual_code = (
                f"{normalized_manual_code[:5]}-{normalized_manual_code[5:]}"
            )
            try:
                expires_at = db.create_pairing(
                    credential,
                    session_id,
                    pairing_qr_digest(parsed_token, db.config.pepper),
                    pairing_manual_digest(
                        normalized_manual_code, db.config.pepper
                    ),
                )
                break
            except PairingCodeCollision:
                continue
            except AuthenticationFailed:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=AUTHENTICATION_ERROR,
                    headers={"WWW-Authenticate": "Bearer"},
                ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to create pairing",
            )
        return {
            "api_version": 1,
            "pairing_token": pairing_token,
            "manual_code": manual_code,
            "expires_at": expires_at,
            "deep_link": f"flightmargin://pair/v1?token={pairing_token}",
        }

    @application.post("/v1/pairings/claim")
    def claim_pairing(
        claim: PairingClaim,
        db: RelayDatabase = Depends(database),
    ) -> dict:
        try:
            device_credential = parse_credential(claim.credential, "device")
        except InvalidCredential:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Malformed device credential",
            ) from None

        parsed_token = None
        normalized_manual_code = None
        try:
            if claim.pairing_token is not None:
                parsed_token = parse_pairing_token(claim.pairing_token)
            else:
                normalized_manual_code = normalize_manual_code(claim.manual_code)
        except InvalidCredential:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Malformed pairing credential",
            ) from None
        try:
            host_id = db.claim_pairing(
                claim,
                device_credential,
                pairing_token=parsed_token,
                normalized_manual_code=normalized_manual_code,
            )
        except PairingFailed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PAIRING_ERROR,
            ) from None
        return {
            "api_version": 1,
            "paired": True,
            "device_id": claim.device_id,
            "host_id": host_id,
        }

    @application.get("/v1/quota")
    def get_quota(
        authorization: str | None = Header(default=None),
        db: RelayDatabase = Depends(database),
    ) -> dict:
        credential = _bearer_credential(authorization, "device")
        try:
            return db.get_quota(credential)
        except AuthenticationFailed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTHENTICATION_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

    return application


app = create_app()
