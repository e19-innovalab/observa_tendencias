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

export const UsersPageSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(UserSchema),
});

export const AuthOptionsSchema = z.object({
  roles: z.array(z.object({ role: z.string(), label: z.string(), permissions: z.array(z.string()) })),
  statuses: z.record(z.string(), z.string()),
  password_min_length: z.number(),
  default_role: z.string(),
});

/** Permisos que define el backend (app.yaml -> auth.roles). */
export const PERMISSIONS = {
  view: 'view',
  manageData: 'manage_data',
  manageUsers: 'manage_users',
} as const;
