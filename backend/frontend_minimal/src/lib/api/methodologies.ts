import { z } from 'zod';
import { MethodologyItemSchema } from '../schemas/api';
import { apiGet } from './client';

/** Versiones de una metodología; is_current marca las que usa la configuración actual. */
export const getMethodologies = (type: string) => apiGet(`/methodologies/${type}`, z.array(MethodologyItemSchema), {}, 600);
