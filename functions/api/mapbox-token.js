// Hands the Mapbox public token to the story page (/story/).
// The token lives in the Cloudflare Pages secret MAPBOX_TOKEN, not in this repository.
// A public (pk.) token is visible to anyone who opens the page; what protects it is the URL restriction
// set on the token in the Mapbox account (this site's addresses only) and its public-only scopes.
export async function onRequestGet({ env }) {
  const token = env.MAPBOX_TOKEN || '';
  const ok = token.startsWith('pk.');
  return new Response(JSON.stringify(ok ? { token } : { error: token ? 'MAPBOX_TOKEN must be a public (pk.) token.' : 'Mapbox is not set up yet.' }), {
    status: ok ? 200 : 503,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, max-age=300' },
  });
}
