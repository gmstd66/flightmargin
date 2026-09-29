"""Separate FastAPI application for the FlightMargin mobile relay."""

from fastapi import Depends, FastAPI, Header, HTTPException, status

from relay.config import RelayConfig
from relay.credentials import (
    CREDENTIAL_MAX_LENGTH,
    InvalidCredential,
    parse_credential,
)
from relay.database import (
    AuthenticationFailed,
    RegistrationConflict,
    RelayDatabase,
)
from relay.models import HostRegistration, QuotaReport


AUTHENTICATION_ERROR = "Invalid or revoked credential"


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
