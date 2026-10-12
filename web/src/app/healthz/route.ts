/** Liveness probe for Docker: answers without touching the API. */
export function GET() {
  return Response.json({ status: "ok" });
}
