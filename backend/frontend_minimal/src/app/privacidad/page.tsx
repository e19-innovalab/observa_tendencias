import type { Metadata } from 'next';
import Link from 'next/link';
import { Logo } from '@/components/brand/Logo';

export const metadata: Metadata = { title: 'Privacidad' };

/** Qué datos de las cuentas guarda el observatorio. Pública: se enlaza desde el ingreso con Google. */
export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12 text-sm leading-relaxed text-body">
      <Logo href="/login" />
      <h1 className="text-2xl font-semibold text-heading">Privacidad</h1>
      <section className="space-y-2">
        <h2 className="font-semibold text-heading">Qué guardamos</h2>
        <p>
          De cada cuenta guardamos el nombre, el correo, el rol, la fecha de alta y la del último
          ingreso. Si entrás con Google, Google nos pasa solo tu nombre, tu correo y un identificador
          de tu cuenta: no tenemos acceso a tu correo, tus archivos ni tu contraseña de Google. En las
          cuentas con acceso completo también guardamos las preguntas al asistente y sus respuestas,
          para cuidar el límite diario y revisar la calidad. Las preguntas las responde un modelo de
          inteligencia artificial de un servicio externo, que las recibe sin tu nombre ni tu correo.
        </p>
      </section>
      <section className="space-y-2">
        <h2 className="font-semibold text-heading">Para qué</h2>
        <p>
          Solo para darte acceso y saber qué secciones podés ver. No compartimos ni vendemos estos
          datos.
        </p>
      </section>
      <section className="space-y-2">
        <h2 className="font-semibold text-heading">Borrar tu cuenta</h2>
        <p>Pedíselo a un administrador del observatorio y la damos de baja.</p>
      </section>
      <p>
        <Link href="/login" className="font-semibold text-brand underline">Volver al ingreso</Link>
      </p>
    </main>
  );
}
