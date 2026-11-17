import { z } from 'zod';

/** Usuario del observatorio (GET /auth/me, /users). */
export const UserSchema = z.object({
  user_id: z.number(),
  email: z.string(),
  full_name: z.string(),
  role: z.string(),
  role_label: z.string(),
  permissions: z.array(z.string()),
  sector_code: z.string().nullable(),
  sector_name: z.string().nullable(),
  countries: z.array(z.string()), // vacío = toda la región
  status: z.string(),
  status_label: z.string(),
  created_at: z.string(),
  last_login_at: z.string().nullable(),
});
export type User = z.infer<typeof UserSchema>;

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_at: z.string(),
  user: UserSchema,
});

/** Permisos que define el backend (app.yaml -> auth.roles). */
export const PERMISSIONS = {
  view: 'view',
  manageData: 'manage_data',
  manageUsers: 'manage_users',
} as const;
