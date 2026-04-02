import { apiFetch } from './client';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  PaginatedResponse,
} from './types';

export function listProjects(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<Project>> {
  return apiFetch<PaginatedResponse<Project>>(
    `/api/projects?page=${page}&page_size=${pageSize}`,
  );
}

export function getProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/projects/${id}`);
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return apiFetch<Project>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateProject(
  id: string,
  data: ProjectUpdate,
): Promise<Project> {
  return apiFetch<Project>(`/api/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/projects/${id}`, { method: 'DELETE' });
}
