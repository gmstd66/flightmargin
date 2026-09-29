import { createHandler } from "./router.ts";

const handler = createHandler({
  // Application code logs only this safe request ID; it never logs request bodies,
  // pairing material, Authorization headers, or raw client IPs.
  onInternalError: (requestId) => console.error(`relay-v1 failure ${requestId}`),
});

Deno.serve(handler);
