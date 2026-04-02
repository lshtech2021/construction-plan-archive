import { apiFetch } from './client';
import type { Sheet, SheetDetail, ItemsResponse } from './types';

export function listSheets(
  documentId: string,
  discipline?: string,
  sheetType?: string,
): Promise<ItemsResponse<Sheet>> {
  const params = new URLSearchParams();
  if (discipline) params.set('discipline', discipline);
  if (sheetType) params.set('sheet_type', sheetType);
  const qs = params.toString();
  return apiFetch<ItemsResponse<Sheet>>(
    `/api/documents/${documentId}/sheets${qs ? `?${qs}` : ''}`,
  );
}

export function getSheet(id: string): Promise<SheetDetail> {
  return apiFetch<SheetDetail>(`/api/sheets/${id}`);
}
