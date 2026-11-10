/**
 * WIN OS API client for the existing WIN web application (web-app branch).
 *
 * Usage on the web-app branch (docs/backend.js integration point):
 *   <script src="win-api-client.js"></script>
 *   const win = new WinApiClient({ baseUrl: "https://win.example.org", apiKey: "..." });
 *   const assets = await win.listAssets();
 *
 * Honesty contract (unchanged from the existing app): when the API is not
 * configured or unreachable, methods resolve to { available: false, reason }
 * so the UI can show its explicit empty/unavailable state. This client never
 * fabricates data and never falls back to demo data silently.
 */
class WinApiClient {
  constructor({ baseUrl = "", apiKey = "" } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
  }
  get configured() { return Boolean(this.baseUrl); }

  async _get(path) {
    if (!this.configured) return { available: false, reason: "WIN API not configured" };
    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        headers: { "X-API-Key": this.apiKey } });
      if (!resp.ok) return { available: false, reason: `WIN API returned ${resp.status}` };
      return { available: true, data: await resp.json() };
    } catch (err) {
      return { available: false, reason: `WIN API unreachable: ${err.message}` };
    }
  }
  health() { return this._get("/health/ready"); }
  listAssets() { return this._get("/api/v1/assets"); }
  listFacilities() { return this._get("/api/v1/facilities"); }
  listCollections() { return this._get("/api/v1/collections"); }
  dataQuality() { return this._get("/api/v1/data-quality/summary"); }
  copilotStatus() { return this._get("/api/v1/copilot/status"); }
}
if (typeof module !== "undefined") module.exports = { WinApiClient };
