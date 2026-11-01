/** The constructor HTTP boundary. Responses retain their JSON or ZIP format. */
export const API_BASE = '/creature-workshop/constructor';
export function createApi({ fetch: fetchImpl = globalThis.fetch, baseUrl = API_BASE } = {}) {
  async function request(path, payload, signal) {
    const response = await fetchImpl(baseUrl + path, {
      method: payload ? 'POST' : 'GET',
      headers: payload ? { 'Content-Type': 'application/json' } : {},
      body: payload ? JSON.stringify(payload) : undefined,
      signal,
    });
    if (!response.ok) {
      let message = `Ошибка ${response.status}`;
      try {
        message = (await response.json()).error || message;
      } catch {}
      throw Error(message);
    }
    return response;
  }
  return { request, baseUrl };
}
export function download(
  name,
  blob,
  { document = globalThis.document, url = globalThis.URL } = {},
) {
  const a = document.createElement('a'),
    objectUrl = url.createObjectURL(blob);
  a.href = objectUrl;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => url.revokeObjectURL(objectUrl), 2000);
}
