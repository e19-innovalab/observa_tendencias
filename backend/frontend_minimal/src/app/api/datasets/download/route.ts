import { NextResponse } from 'next/server';
import { getToken } from '@/lib/auth/session';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8010';
const SAFE = /^[a-z0-9_]+$/;

/**
 * Descarga la plantilla de un formato (?profile=&format=xlsx|csv) o un archivo de ejemplo
 * (?profile=&example=nombre) desde el backend, con la sesión.
 */
export async function GET(request: Request) {
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: null }, { status: 401 });
  const sp = new URL(request.url).searchParams;
  const profile = sp.get('profile') ?? '';
  const example = sp.get('example');
  const format = sp.get('format') === 'csv' ? 'csv' : 'xlsx';
  if (!SAFE.test(profile) || (example !== null && !SAFE.test(example))) {
    return NextResponse.json({ detail: null }, { status: 400 });
  }
  const path = example
    ? `/api/v1/datasets/profiles/${profile}/examples/${example}`
    : `/api/v1/datasets/profiles/${profile}/template?format=${format}`;
  const res = await fetch(new URL(path, BASE_URL), { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
  if (!res.ok) return NextResponse.json({ detail: null }, { status: res.status });
  return new NextResponse(res.body, {
    headers: {
      'Content-Type': res.headers.get('content-type') ?? 'application/octet-stream',
      'Content-Disposition': res.headers.get('content-disposition') ?? 'attachment',
    },
  });
}
