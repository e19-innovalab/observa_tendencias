import { MotionPageSchema } from '../schemas/motion';
import { apiGet } from './client';

export const getMotion = (y?: string) => apiGet('/occupation-groups/motion', MotionPageSchema, { y }, 300);
