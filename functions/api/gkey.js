// Hands the Google Maps Platform key to the Explore page (/explore/).
// The key lives in the Cloudflare Pages variable GOOGLE_MAPS_KEY, not in this repository.
// A browser key is visible to anyone who opens the page; what protects it is the website and API restrictions
// set on the key in the Google Cloud console (this site's address only; Maps JavaScript, Map Tiles and Places only).
export async function onRequestGet({ env }) {
  const key = env.GOOGLE_MAPS_KEY || '';
  return new Response(JSON.stringify(key ? { key } : { error: 'Google Maps is not set up yet.' }), {
    status: key ? 200 : 503,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, max-age=300' },
  });
}
