import { NextResponse } from 'next/server';
import { ApiError, apiSend } from '@/lib/api/client';
import { getToken } from '@/lib/auth/session';
import { AssistantAnswerSchema } from '@/lib/schemas/assistant';

/** Pedido cancelado por quien preguntó (el mismo código que usa el backend). */
const CANCELLED = 499;

/**
 * Pregunta al asistente (POST /assistant/ask) con la sesión de la cookie, que el navegador no puede
 * leer. Devuelve la respuesta del backend o {detail} con el mismo código de error. Si la persona
 * cancela, el pedido al backend se corta también y el backend detiene el modelo.
 */
export async function POST(request: Request) {
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: null }, { status: 401 });
  try {
    const answer = await apiSend('POST', '/assistant/ask', AssistantAnswerSchema, await request.json(), {
      token,
      signal: request.signal,
    });
    return NextResponse.json(answer);
  } catch (e) {
    if (request.signal.aborted) return new NextResponse(null, { status: CANCELLED });
    const status = e instanceof ApiError && e.status ? e.status : 502;
    return NextResponse.json({ detail: e instanceof ApiError ? e.message : null }, { status });
  }
}
