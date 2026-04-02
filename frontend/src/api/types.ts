export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Project {
  id: string;
  name: string;
  client?: string;
  location?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  client?: string;
  location?: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  client?: string;
  location?: string;
  description?: string;
}

export interface Document {
  id: string;
  project_id: string;
  original_filename: string;
  stored_path: string;
  file_size_bytes: number;
  page_count?: number;
  processing_status: ProcessingStatus;
  processing_error?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatus {
  id: string;
  processing_status: ProcessingStatus;
  page_count?: number;
  processing_error?: string;
  sheets_processed: number;
}

export interface Sheet {
  id: string;
  document_id: string;
  page_number: number;
  sheet_number?: string;
  sheet_title?: string;
  discipline: string;
  sheet_type: string;
  image_path?: string;
  thumbnail_path?: string;
  extraction_confidence: string;
  needs_human_review: boolean;
  text_embedding_id?: string;
  image_embedding_id?: string;
  created_at: string;
  updated_at: string;
}

export interface SheetDetail extends Sheet {
  native_text?: string;
  ocr_text?: string;
  vlm_description?: string;
  merged_text?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ItemsResponse<T> {
  items: T[];
  total: number;
}

export interface SearchRequest {
  query: string;
  search_type?: 'hybrid' | 'semantic' | 'keyword';
  discipline?: string;
  sheet_type?: string;
  project_id?: string;
  limit?: number;
}

export interface SearchResult {
  sheet: Sheet;
  score: number;
  highlight?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  search_type: string;
}

export interface SimilarRequest {
  sheet_id: string;
  limit?: number;
}

export interface SearchStatus {
  total_sheets: number;
  indexed_text: number;
  indexed_image: number;
  pending_indexing: number;
}
