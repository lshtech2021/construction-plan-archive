import { apiFetch } from './client';
import type {
  SearchRequest,
  SearchResponse,
  SimilarRequest,
  SearchStatus,
} from './types';

export function search(req: SearchRequest): Promise<SearchResponse> {
  return apiFetch<SearchResponse>('/api/search', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function searchSimilar(req: SimilarRequest): Promise<SearchResponse> {
  return apiFetch<SearchResponse>('/api/search/similar', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function getSearchStatus(): Promise<SearchStatus> {
  return apiFetch<SearchStatus>('/api/search/status');
}
