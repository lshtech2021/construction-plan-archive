import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getDocument, getDocumentStatus } from '../api/documents';
import { listSheets } from '../api/sheets';
import type { Document, DocumentStatus, Sheet } from '../api/types';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Badge } from '../components/ui/Badge';

const POLL_INTERVAL = 4000;

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [document, setDocument] = useState<Document | null>(null);
  const [status, setStatus] = useState<DocumentStatus | null>(null);
  const [sheets, setSheets] = useState<Sheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current != null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    if (!id) return;
    Promise.all([getDocument(id), getDocumentStatus(id), listSheets(id)])
      .then(([doc, st, sh]) => {
        setDocument(doc);
        setStatus(st);
        setSheets(sh.items);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

    return stopPolling;
  }, [id]);

  // Poll while processing
  useEffect(() => {
    if (!id || !status) return;
    if (
      status.processing_status === 'pending' ||
      status.processing_status === 'processing'
    ) {
      pollRef.current = setInterval(async () => {
        try {
          const [st, sh] = await Promise.all([
            getDocumentStatus(id),
            listSheets(id),
          ]);
          setStatus(st);
          setSheets(sh.items);
          if (
            st.processing_status !== 'pending' &&
            st.processing_status !== 'processing'
          ) {
            stopPolling();
          }
        } catch {
          stopPolling();
        }
      }, POLL_INTERVAL);
    }
    return stopPolling;
  }, [id, status?.processing_status]);

  if (loading) return <LoadingSpinner className="py-16" />;
  if (error)
    return (
      <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>
    );
  if (!document || !status) return null;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          {document.original_filename}
        </h2>
        <p className="text-sm text-gray-500">
          {(document.file_size_bytes / 1024).toFixed(1)} KB
          {document.page_count != null ? ` · ${document.page_count} pages` : ''}
        </p>
      </div>

      {/* Status Card */}
      <Card className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">
              Processing Status
            </p>
            <div className="mt-1 flex items-center gap-3">
              <StatusBadge status={status.processing_status} />
              {(status.processing_status === 'pending' ||
                status.processing_status === 'processing') && (
                <span className="text-xs text-gray-500">Auto-refreshing…</span>
              )}
            </div>
            {status.processing_error && (
              <p className="mt-2 text-sm text-red-600">
                {status.processing_error}
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold text-gray-900">
              {status.sheets_processed}
            </p>
            <p className="text-xs text-gray-500">sheets processed</p>
          </div>
        </div>
      </Card>

      {/* Sheets */}
      <h3 className="mb-3 text-sm font-medium text-gray-700">
        Sheets ({sheets.length})
      </h3>
      {sheets.length === 0 ? (
        <EmptyState
          title="No sheets yet"
          description={
            status.processing_status === 'completed'
              ? 'No sheets were extracted from this document.'
              : 'Sheets will appear here once processing is complete.'
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sheets.map((sheet) => (
            <Link key={sheet.id} to={`/sheets/${sheet.id}`}>
              <Card className="hover:border-blue-300">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {sheet.sheet_number ?? `Page ${sheet.page_number}`}
                  </span>
                  <Badge color="blue">{sheet.discipline}</Badge>
                </div>
                {sheet.sheet_title && (
                  <p className="mb-1 text-sm text-gray-600">
                    {sheet.sheet_title}
                  </p>
                )}
                <p className="text-xs text-gray-400">{sheet.sheet_type}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
