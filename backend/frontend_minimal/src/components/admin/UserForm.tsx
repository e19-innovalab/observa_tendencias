'use client';

import { useActionState } from 'react';
import { createUser, updateUser, type FormState } from '@/lib/admin/actions';
import type { User } from '@/lib/schemas/auth';

type Option = { value: string; label: string };
type Props = {
  user?: User; // sin usuario: alta
  roles: Option[];
  statuses: Option[];
  sectors: Option[];
  countries: Option[];
  passwordMin: number;
  defaultRole: string;
};

const input = 'w-full rounded-md border border-line bg-white px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus';
const labelCls = 'mb-1 block text-xs font-semibold text-muted-text';

/** Alta o edición de una cuenta. Los valores posibles (roles, estados) vienen del backend. */
export function UserForm({ user, roles, statuses, sectors, countries, passwordMin, defaultRole }: Props) {
  const action = user ? updateUser.bind(null, user.user_id) : createUser;
  const [state, formAction, pending] = useActionState<FormState, FormData>(action, {});
  return (
    <form action={formAction} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {!user && (
        <label>
          <span className={labelCls}>Correo electrónico</span>
          <input name="email" type="email" required className={input} autoComplete="off" />
        </label>
      )}
      <label>
        <span className={labelCls}>Nombre y apellido</span>
        <input name="full_name" required defaultValue={user?.full_name} className={input} />
      </label>
      <label>
        <span className={labelCls}>Rol</span>
        <select name="role" defaultValue={user?.role ?? defaultRole} className={input}>
          {roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </label>
      <label>
        <span className={labelCls}>Sector de interés</span>
        <select name="sector_code" defaultValue={user?.sector_code ?? ''} className={input}>
          <option value="">Todos (transversal)</option>
          {sectors.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </label>
      <fieldset>
        <legend className={labelCls}>Países (ninguno = toda la región)</legend>
        <div className="flex gap-3 pt-1.5">
          {countries.map((c) => (
            <label key={c.value} className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" name="countries" value={c.value} defaultChecked={user?.countries.includes(c.value)} /> {c.label}
            </label>
          ))}
        </div>
      </fieldset>
      {user && (
        <label>
          <span className={labelCls}>Estado</span>
          <select name="status" defaultValue={user.status} className={input}>
            {statuses.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
      )}
      <label>
        <span className={labelCls}>{user ? 'Nueva contraseña (opcional)' : 'Contraseña inicial'}</span>
        <input name="password" type="password" required={!user} minLength={passwordMin} className={input} autoComplete="new-password" placeholder={`Mínimo ${passwordMin} caracteres`} />
      </label>
      <div className="flex items-end gap-3 md:col-span-2 lg:col-span-3">
        <button type="submit" disabled={pending} className="rounded-md bg-heading px-4 py-2 text-sm font-medium text-white hover:bg-brand disabled:opacity-60">
          {pending ? 'Guardando…' : user ? 'Guardar cambios' : 'Crear cuenta'}
        </button>
        {state.error && <p role="alert" className="text-sm text-alert-critical-text">{state.error}</p>}
        {state.message && <p role="status" className="text-sm text-success">{state.message}</p>}
      </div>
    </form>
  );
}
