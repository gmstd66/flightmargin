import {
  normalizeManualCode,
  parseCredential,
  parsePairingToken,
  rateLimitIdentityDigest,
} from "./crypto.ts";
import { pepperFromEnvironment, PostgresRelayRepository } from "./db.ts";
import {
  AuthenticationFailed,
  PairingFailed,
  PairingUnavailable,
  RegistrationConflict,
  type RelayRepository,
} from "./types.ts";
import {
  validatePairingClaim,
  validateQuota,
  validateRegistration,
} from "./validation.ts";

const BODY_LIMIT = 16 * 1024;
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const AUTHENTICATION_ERROR = "Invalid or revoked credential";
const PAIRING_ERROR = "Pairing could not be completed";
const ROUTES = new Map<string, Set<string>>([
  ["/health", new Set(["GET"])],
  ["/v1/hosts/register", new Set(["POST"])],
  ["/v1/quota", new Set(["PUT", "GET"])],
  ["/v1/pairings", new Set(["POST"])],
  ["/v1/pairings/claim", new Set(["POST"])],
]);

function response(
  status: number,
  body: Record<string, unknown>,
  requestId: string,
  headers: HeadersInit = {},
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...JSON_HEADERS, "x-request-id": requestId, ...headers },
  });
}

function errorResponse(
  status: number,
  detail: string,
  requestId: string,
  headers: HeadersInit = {},
): Response {
  return response(status, { detail }, requestId, headers);
}

function requestId(request: Request): string {
  const supplied = request.headers.get("x-request-id");
  return supplied && /^[A-Za-z0-9._-]{1,80}$/.test(supplied)
    ? supplied
    : crypto.randomUUID();
}

function routePath(url: URL): string {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  return path.startsWith("/relay-v1/") ? path.slice("/relay-v1".length) : path;
}

async function jsonBody(request: Request): Promise<unknown> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0].trim()
    .toLowerCase();
  if (contentType !== "application/json") {
    throw new HttpFailure(415, "Unsupported Media Type");
  }
  const declared = request.headers.get("content-length");
  if (declared && Number(declared) > BODY_LIMIT) {
    throw new HttpFailure(413, "Request body too large");
  }
  if (!request.body) throw new HttpFailure(422, "Invalid request body");
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > BODY_LIMIT) {
      await reader.cancel();
      throw new HttpFailure(413, "Request body too large");
    }
    chunks.push(value);
  }
  const joined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    joined.set(chunk, offset);
    offset += chunk.length;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(joined));
  } catch {
    throw new HttpFailure(422, "Invalid request body");
  }
}

function bearer(request: Request, kind: "host" | "device") {
  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Bearer ")) throw new AuthenticationFailed();
  const token = authorization.slice(7);
  if (!token || token.includes(" ")) throw new AuthenticationFailed();
  try {
    return parseCredential(token, kind);
  } catch {
    throw new AuthenticationFailed();
  }
}

function ipIdentity(request: Request): string {
  for (const header of ["cf-connecting-ip", "x-real-ip"]) {
    const value = request.headers.get(header)?.trim();
    if (
      value && value.length <= 128 &&
      Array.from(value).every((character) => {
        const code = character.charCodeAt(0);
        return code > 32 && code !== 127;
      })
    ) return value;
  }
  return "unknown";
}

class HttpFailure extends Error {
  constructor(readonly status: number, readonly detail: string) {
    super(detail);
  }
}

export interface HandlerOptions {
  repository?: RelayRepository;
  pepper?: Uint8Array;
  onInternalError?: (requestId: string) => void;
}

export function createHandler(options: HandlerOptions = {}) {
  let repository = options.repository;
  let pepper = options.pepper;
  const dependencies = () => {
    pepper ??= pepperFromEnvironment();
    repository ??= new PostgresRelayRepository(pepper);
    return { repository, pepper };
  };

  return async (request: Request): Promise<Response> => {
    const id = requestId(request);
    const path = routePath(new URL(request.url));
    const methods = ROUTES.get(path);
    if (!methods) return errorResponse(404, "Not Found", id);
    if (!methods.has(request.method)) {
      return errorResponse(405, "Method Not Allowed", id, {
        allow: Array.from(methods).join(", "),
      });
    }
    if (path === "/health") return response(200, { status: "ok" }, id);

    try {
      const configured = dependencies();
      if (path === "/v1/hosts/register") {
        const identityDigest = await rateLimitIdentityDigest(
          ipIdentity(request),
          configured.pepper,
        );
        const limit = await configured.repository.rateLimit(
          "host-registration",
          identityDigest,
          3600,
          10,
        );
        if (!limit.allowed) {
          return errorResponse(429, "Too many requests", id, {
            "retry-after": String(limit.retryAfter),
          });
        }
        let parsedRegistration;
        try {
          const registration = validateRegistration(await jsonBody(request));
          parsedRegistration = {
            registration,
            credential: parseCredential(registration.credential, "host"),
          };
        } catch (error) {
          if (error instanceof HttpFailure) throw error;
          return errorResponse(422, "Malformed host registration", id);
        }
        try {
          const created = await configured.repository.registerHost(
            parsedRegistration.registration,
            parsedRegistration.credential,
          );
          return response(201, {
            api_version: 1,
            host_id: parsedRegistration.registration.hostId,
            registered: created,
            result: created ? "registered" : "already_registered",
          }, id);
        } catch (error) {
          if (error instanceof RegistrationConflict) {
            return errorResponse(
              409,
              "Host or credential identifier is already registered",
              id,
            );
          }
          throw error;
        }
      }

      if (path === "/v1/quota" && request.method === "PUT") {
        const credential = bearer(request, "host");
        let report;
        try {
          report = validateQuota(await jsonBody(request));
        } catch (error) {
          if (error instanceof HttpFailure) throw error;
          return errorResponse(422, "Invalid quota report", id);
        }
        const accepted = await configured.repository.putQuota(credential, report);
        return response(200, {
          result: accepted ? "accepted" : "stale",
          sampled_at: report.sampledAt,
        }, id);
      }

      if (path === "/v1/quota") {
        const credential = bearer(request, "device");
        return response(200, await configured.repository.getQuota(credential), id);
      }

      if (path === "/v1/pairings") {
        const credential = bearer(request, "host");
        let pairing;
        try {
          pairing = await configured.repository.createPairing(credential);
        } catch (error) {
          if (error instanceof PairingUnavailable) {
            return errorResponse(503, "Unable to create pairing", id);
          }
          throw error;
        }
        return response(201, {
          api_version: 1,
          pairing_token: pairing.pairingToken,
          manual_code: pairing.manualCode,
          expires_at: pairing.expiresAt,
          deep_link: `flightmargin://pair/v1?token=${pairing.pairingToken}`,
        }, id);
      }

      const identityDigest = await rateLimitIdentityDigest(
        ipIdentity(request),
        configured.pepper,
      );
      const limit = await configured.repository.rateLimit(
        "pairing-claim",
        identityDigest,
        300,
        20,
      );
      if (!limit.allowed) {
        return errorResponse(429, "Too many requests", id, {
          "retry-after": String(limit.retryAfter),
        });
      }
      let parsedClaim;
      try {
        const claim = validatePairingClaim(await jsonBody(request));
        parsedClaim = {
          claim,
          credential: parseCredential(claim.credential, "device"),
          method: claim.pairingToken
            ? { token: parsePairingToken(claim.pairingToken) }
            : { manualCode: normalizeManualCode(claim.manualCode) },
        };
      } catch (error) {
        if (error instanceof HttpFailure) throw error;
        return errorResponse(422, "Malformed pairing claim", id);
      }
      try {
        const hostId = await configured.repository.claimPairing(
          parsedClaim.claim,
          parsedClaim.credential,
          parsedClaim.method,
        );
        return response(200, {
          api_version: 1,
          paired: true,
          device_id: parsedClaim.claim.deviceId,
          host_id: hostId,
        }, id);
      } catch (error) {
        if (error instanceof PairingFailed) {
          return errorResponse(400, PAIRING_ERROR, id);
        }
        throw error;
      }
    } catch (error) {
      if (error instanceof AuthenticationFailed) {
        return errorResponse(401, AUTHENTICATION_ERROR, id, {
          "www-authenticate": "Bearer",
        });
      }
      if (error instanceof HttpFailure) {
        return errorResponse(error.status, error.detail, id);
      }
      options.onInternalError?.(id);
      return errorResponse(500, "Internal server error", id);
    }
  };
}
