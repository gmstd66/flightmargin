export type CredentialKind = "host" | "device";

export interface ParsedCredential {
  kind: CredentialKind;
  credentialId: string;
  secret: string;
}

export interface ParsedPairingToken {
  sessionId: string;
  secret: string;
}

export interface HostRegistration {
  hostId: string;
  displayName: string;
  platform: string;
  appVersion: string | null;
  credential: string;
}

export interface QuotaReport {
  schemaVersion: 1;
  sampledAt: string;
  fiveHourUsed: number | null;
  fiveHourResetAt: string | null;
  weeklyUsed: number | null;
  weeklyResetAt: string | null;
  planType: string | null;
  resetCreditsAvailable: number | null;
  creditsBalance: number | null;
  spendControlReached: boolean | null;
  rateLimitReachedType: string | null;
  collectorState: "ok" | "degraded" | "error";
  collectorMessageCode: string | null;
}

export interface PairingClaim {
  pairingToken: string | null;
  manualCode: string | null;
  deviceId: string;
  displayName: string;
  platform: string;
  credential: string;
}

export interface PairingResult {
  pairingToken: string;
  manualCode: string;
  expiresAt: string;
}

export interface RateLimitResult {
  allowed: boolean;
  retryAfter: number;
}

export type PairingMethod =
  | { token: ParsedPairingToken; manualCode?: never }
  | { token?: never; manualCode: string };

export interface RelayRepository {
  rateLimit(
    action: "host-registration" | "pairing-claim",
    identityDigest: string,
    windowSeconds: number,
    limit: number,
  ): Promise<RateLimitResult>;
  registerHost(
    registration: HostRegistration,
    credential: ParsedCredential,
  ): Promise<boolean>;
  putQuota(
    credential: ParsedCredential,
    report: QuotaReport,
  ): Promise<boolean>;
  createPairing(credential: ParsedCredential): Promise<PairingResult>;
  claimPairing(
    claim: PairingClaim,
    credential: ParsedCredential,
    method: PairingMethod,
  ): Promise<string>;
  getQuota(credential: ParsedCredential): Promise<Record<string, unknown>>;
}

export class AuthenticationFailed extends Error {}
export class RegistrationConflict extends Error {}
export class PairingFailed extends Error {}
export class PairingUnavailable extends Error {}
