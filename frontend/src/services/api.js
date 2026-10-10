const BASE = import.meta.env.VITE_API_URL || '';
export const mediaUrl = path => path ? `${BASE}${path}` : '';
export async function api(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) throw new Error((await response.json()).detail || 'Request failed');
  return response.json();
}
