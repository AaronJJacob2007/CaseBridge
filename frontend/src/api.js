export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function readResponse(response) {
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError('The service returned an unreadable response. Please retry.', response.status);
  }
  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join('; ')
      : data?.detail;
    throw new ApiError(detail || 'The request could not be completed.', response.status, data);
  }
  return data;
}

export async function loadDemoUsers({ signal, baseUrl = '' } = {}) {
  // Only the initial identity catalog is read without a selected demo user.
  return readResponse(await fetch(baseUrl + '/api/demo/users', { signal }));
}

export function createApi(userId, { baseUrl = '' } = {}) {
  if (!Number.isSafeInteger(Number(userId)) || Number(userId) <= 0) {
    throw new ApiError('Select a valid demo user.');
  }
  return async function api(path, { method = 'GET', body, signal, responseType = 'json' } = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) {
      throw new ApiError('Invalid service path.');
    }
    if (!['json', 'blob'].includes(responseType)) throw new ApiError('Invalid response type.');
    const headers = { 'X-User-Id': String(userId) };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(baseUrl + '/api' + path, {
      method, headers, signal,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    if (responseType === 'blob' && response.ok) {
      if (!/^text\/csv(?:;|$)/i.test(response.headers.get('content-type') || '')) {
        throw new ApiError('The service did not return a CSV file. Please retry.', response.status);
      }
      return response.blob();
    }
    return readResponse(response);
  };
}
