import { z } from 'zod';
import {
  DatasetFileSchema,
  DatasetProfileSchema,
  DatasetUploadResultSchema,
  type DatasetFile,
  type DatasetUploadResult,
} from '../schemas/datasets';
import { apiGet, apiSend, apiSendForm } from './client';

export const getDatasetProfiles = () =>
  apiGet('/datasets/profiles', z.array(DatasetProfileSchema), {}, 3600);

export const getDatasets = (params: { profile?: string; origin?: string; limit: number }) =>
  apiGet('/datasets', z.array(DatasetFileSchema), params, 0);

/** Paso 1 de la carga manual: guarda el archivo y devuelve el reporte de validación. */
export const uploadDataset = (form: FormData, token: string): Promise<DatasetUploadResult> =>
  apiSendForm('/datasets/upload', DatasetUploadResultSchema, form, { token });

/** Paso 2: carga el archivo validado. confirmOverlap acepta repetir valores oficiales. */
export async function commitDataset(
  datasetId: number,
  confirmOverlap: boolean,
  token: string,
): Promise<DatasetFile> {
  const dataset = await apiSend(
    'POST',
    `/datasets/${datasetId}/commit`,
    DatasetFileSchema,
    { confirm_overlap: confirmOverlap },
    { token },
  );
  if (!dataset) throw new Error('El backend no devolvió el archivo cargado.');
  return dataset;
}
