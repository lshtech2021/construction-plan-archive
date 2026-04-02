import { apiFetch, apiUpload } from './client';
import type { Document, DocumentStatus, ItemsResponse } from './types';

export function listDocuments(
  projectId: string,
): Promise<ItemsResponse<Document>> {
  return apiFetch<ItemsResponse<Document>>(
    `/api/projects/${projectId}/documents`,
  );
}

export function getDocument(id: string): Promise<Document> {
  return apiFetch<Document>(`/api/documents/${id}`);
}

export function getDocumentStatus(id: string): Promise<DocumentStatus> {
  return apiFetch<DocumentStatus>(`/api/documents/${id}/status`);
}

export function uploadDocument(
  projectId: string,
  file: File,
): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  return apiUpload<Document>(
    `/api/projects/${projectId}/documents/upload`,
    formData,
  );
}
