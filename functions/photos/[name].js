// Serves photos from the R2 bucket bound as PHOTOS: GET /photos/{uuid}.jpg
export async function onRequestGet({ params, env }) {
  const name = String(params.name || '');
  if (!/^[0-9a-f-]{36}\.jpg$/.test(name)) return new Response('Not found', { status: 404 });
  if (!env.PHOTOS) return new Response('Photo storage is not set up yet', { status: 503 });
  const obj = await env.PHOTOS.get(name);
  if (!obj) return new Response('Not found', { status: 404 });
  return new Response(obj.body, {
    headers: { 'Content-Type': 'image/jpeg', 'Cache-Control': 'public, max-age=31536000, immutable', 'ETag': obj.httpEtag },
  });
}
