import type { CredentialKind, ParsedCredential, ParsedPairingToken } from "./types.ts";

const UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const SECRET_PATTERN = "[A-Za-z0-9_-]{43}";
const CREDENTIAL_PATTERN = new RegExp(
  `^(fmh1|fmd1)\.(${UUID_PATTERN})\.(${SECRET_PATTERN})$`,
);
const PAIRING_PATTERN = new RegExp(
  `^fmp1\.(${UUID_PATTERN})\.(${SECRET_PATTERN})$`,
);
const MANUAL_PATTERN = /^[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{5}$/;
const encoder = new TextEncoder();

export const CREDENTIAL_MAX_LENGTH = 128;
export const PAIRING_TOKEN_MAX_LENGTH = 128;
export const MANUAL_CODE_LENGTH = 11;

function decodeBase64Url(value: string): Uint8Array | null {
  try {
    const normalized = value.replaceAll("-", "+").replaceAll("_", "/") + "=";
    const decoded = Uint8Array.from(
      atob(normalized),
      (character) => character.charCodeAt(0),
    );
    const canonical = btoa(String.fromCharCode(...decoded))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replace(/=+$/, "");
    return constantTimeEqual(canonical, value) ? decoded : null;
  } catch {
    return null;
  }
}

export function constantTimeEqual(left: string, right: string): boolean {
  const leftBytes = encoder.encode(left);
  const rightBytes = encoder.encode(right);
  let difference = leftBytes.length ^ rightBytes.length;
  const length = Math.max(leftBytes.length, rightBytes.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }
  return difference === 0;
}

export function parseCredential(
  value: unknown,
  kind: CredentialKind,
): ParsedCredential {
  if (typeof value !== "string" || value.length > CREDENTIAL_MAX_LENGTH) {
    throw new Error("Malformed credential");
  }
  const match = CREDENTIAL_PATTERN.exec(value);
  const expectedPrefix = kind === "host" ? "fmh1" : "fmd1";
  if (!match || match[1] !== expectedPrefix) {
    throw new Error("Malformed credential");
  }
  const decoded = decodeBase64Url(match[3]);
  if (!decoded || decoded.length !== 32) {
    throw new Error("Malformed credential");
  }
  return { kind, credentialId: match[2], secret: match[3] };
}

export function parsePairingToken(value: unknown): ParsedPairingToken {
  if (typeof value !== "string" || value.length > PAIRING_TOKEN_MAX_LENGTH) {
    throw new Error("Malformed pairing token");
  }
  const match = PAIRING_PATTERN.exec(value);
  if (!match) throw new Error("Malformed pairing token");
  const decoded = decodeBase64Url(match[2]);
  if (!decoded || decoded.length !== 32) {
    throw new Error("Malformed pairing token");
  }
  return { sessionId: match[1], secret: match[2] };
}

export function normalizeManualCode(value: unknown): string {
  if (typeof value !== "string" || !MANUAL_PATTERN.test(value)) {
    throw new Error("Malformed manual code");
  }
  return value.replace("-", "");
}

async function hmacHex(context: string, pepper: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new Uint8Array(pepper).buffer,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const digest = new Uint8Array(
    await crypto.subtle.sign("HMAC", key, encoder.encode(context)),
  );
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function credentialDigest(
  credential: ParsedCredential,
  pepper: Uint8Array,
): Promise<string> {
  return hmacHex(
    `${credential.kind}:${credential.credentialId}:${credential.secret}`,
    pepper,
  );
}

export function pairingQrDigest(
  token: ParsedPairingToken,
  pepper: Uint8Array,
): Promise<string> {
  return hmacHex(`pairing-qr:${token.sessionId}:${token.secret}`, pepper);
}

export function pairingManualDigest(
  normalizedCode: string,
  pepper: Uint8Array,
): Promise<string> {
  return hmacHex(`pairing-manual:${normalizedCode}`, pepper);
}

export function rateLimitIdentityDigest(
  ipIdentity: string,
  pepper: Uint8Array,
): Promise<string> {
  return hmacHex(`rate-limit-ip:${ipIdentity}`, pepper);
}

export function randomSecret(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}
