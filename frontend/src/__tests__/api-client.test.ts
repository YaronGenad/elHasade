import { describe, it, expect } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import { getErrorMessage } from '../api/client';

/** Helper to build a minimal AxiosError. */
function makeAxiosError(
  status?: number,
  detail?: string,
  code?: string
): AxiosError {
  const headers = new AxiosHeaders();
  const config = { headers } as AxiosError['config'];

  if (status === undefined) {
    // Network error — no response
    const err = new AxiosError('Network Error', code, config);
    return err;
  }

  const response = {
    status,
    statusText: '',
    headers: {},
    config,
    data: detail ? { detail } : {},
  };

  return new AxiosError('Request failed', code, config, null, response as never);
}

describe('getErrorMessage', () => {
  it('returns network error message when no response', () => {
    const err = makeAxiosError(undefined);
    const msg = getErrorMessage(err);
    expect(msg).toContain('אין חיבור לשרת');
  });

  it('returns timeout message for ECONNABORTED', () => {
    const err = makeAxiosError(undefined, undefined, 'ECONNABORTED');
    const msg = getErrorMessage(err);
    expect(msg).toContain('ארכה יותר מדי זמן');
  });

  it('returns timeout message when error message includes timeout', () => {
    const headers = new AxiosHeaders();
    const config = { headers } as AxiosError['config'];
    const err = new AxiosError('timeout of 5000ms exceeded', undefined, config);
    const msg = getErrorMessage(err);
    expect(msg).toContain('ארכה יותר מדי זמן');
  });

  it('returns correct message for 400', () => {
    const msg = getErrorMessage(makeAxiosError(400));
    expect(msg).toContain('אינה תקינה');
  });

  it('returns server detail for 400 if provided', () => {
    const msg = getErrorMessage(makeAxiosError(400, 'Custom bad request'));
    expect(msg).toBe('Custom bad request');
  });

  it('returns correct message for 401', () => {
    const msg = getErrorMessage(makeAxiosError(401));
    expect(msg).toContain('להתחבר מחדש');
  });

  it('returns correct message for 403', () => {
    const msg = getErrorMessage(makeAxiosError(403));
    expect(msg).toContain('אין הרשאה');
  });

  it('returns correct message for 404', () => {
    const msg = getErrorMessage(makeAxiosError(404));
    expect(msg).toContain('לא נמצא');
  });

  it('returns correct message for 409', () => {
    const msg = getErrorMessage(makeAxiosError(409));
    expect(msg).toContain('התנגשות');
  });

  it('returns correct message for 422', () => {
    const msg = getErrorMessage(makeAxiosError(422));
    expect(msg).toContain('אינם תקינים');
  });

  it('returns correct message for 429', () => {
    const msg = getErrorMessage(makeAxiosError(429));
    expect(msg).toContain('יותר מדי בקשות');
  });

  it('returns correct message for 500', () => {
    const msg = getErrorMessage(makeAxiosError(500));
    expect(msg).toContain('שגיאת שרת');
  });

  it('returns correct message for 502', () => {
    const msg = getErrorMessage(makeAxiosError(502));
    expect(msg).toContain('אינו זמין');
  });

  it('returns correct message for 503', () => {
    const msg = getErrorMessage(makeAxiosError(503));
    expect(msg).toContain('בתחזוקה');
  });

  it('returns correct message for 504', () => {
    const msg = getErrorMessage(makeAxiosError(504));
    expect(msg).toContain('אינו זמין');
  });

  it('returns generic message for unknown status', () => {
    const msg = getErrorMessage(makeAxiosError(418));
    expect(msg).toContain('שגיאה בלתי צפויה');
  });

  it('returns server detail for unknown status if provided', () => {
    const msg = getErrorMessage(makeAxiosError(418, 'I am a teapot'));
    expect(msg).toBe('I am a teapot');
  });
});
