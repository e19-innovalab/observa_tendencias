import { NextResponse, type NextRequest } from 'next/server';
import { LOGIN_PATH, PRIVATE_PREFIXES, SESSION_COOKIE } from '@/lib/auth/constants';

/**
 * Chequeo optimista: sin cookie de sesión, las rutas privadas van al login (con ?next= para volver).
 * La validación real del token la hace cada página contra el backend (getCurrentUser).
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const isPrivate = PRIVATE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (isPrivate && !request.cookies.has(SESSION_COOKIE)) {
    const url = new URL(LOGIN_PATH, request.url);
    url.searchParams.set('next', `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|webp|ico)$).*)'],
};
