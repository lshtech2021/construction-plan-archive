import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getSheet } from '../api/sheets';
import type { SheetDetail } from '../api/types';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

type Tab = 'native' | 'ocr' | 'vlm' | 'merged';

const tabs: { key: Tab; label: string }[] = [
  { key: 'native', label: 'Native Text' },
  { key: 'ocr', label: 'OCR Text' },
  { key: 'vlm', label: 'VLM Description' },
  { key: 'merged', label: 'Merged Text' },
];

export function SheetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [sheet, setSheet] = useState<SheetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('merged');

  useEffect(() => {
    if (!id) return;
    getSheet(id)
      .then(setSheet)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const textMap: Record<Tab, string | undefined> = {
    native: sheet?.native_text,
    ocr: sheet?.ocr_text,
    vlm: sheet?.vlm_description,
    merged: sheet?.merged_text,
  };

  if (loading) return <LoadingSpinner className="py-16" />;
  if (error)
    return (
      <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>
    );
  if (!sheet) return null;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-gray-900">
            {sheet.sheet_number ?? `Page ${sheet.page_number}`}
          </h2>
          <Badge color="blue">{sheet.discipline}</Badge>
          <Badge color="gray">{sheet.sheet_type}</Badge>
          {sheet.needs_human_review && (
            <Badge color="yellow">Needs Review</Badge>
          )}
        </div>
        {sheet.sheet_title && (
          <p className="mt-1 text-gray-600">{sheet.sheet_title}</p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Thumbnail */}
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-700">
            Sheet Image
          </h3>
          {sheet.thumbnail_path || sheet.image_path ? (
            <img
              src={sheet.thumbnail_path ?? sheet.image_path}
              alt={sheet.sheet_title ?? 'Sheet'}
              className="w-full rounded border border-gray-200 object-contain"
            />
          ) : (
            <div className="flex h-48 items-center justify-center rounded bg-gray-100 text-sm text-gray-400">
              No image available
            </div>
          )}
        </Card>

        {/* Metadata */}
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-700">Metadata</h3>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-gray-500">Page Number</dt>
            <dd className="text-gray-900">{sheet.page_number}</dd>
            <dt className="text-gray-500">Discipline</dt>
            <dd className="text-gray-900">{sheet.discipline}</dd>
            <dt className="text-gray-500">Sheet Type</dt>
            <dd className="text-gray-900">{sheet.sheet_type}</dd>
            <dt className="text-gray-500">Confidence</dt>
            <dd className="text-gray-900">{sheet.extraction_confidence}</dd>
            <dt className="text-gray-500">Needs Review</dt>
            <dd className="text-gray-900">
              {sheet.needs_human_review ? 'Yes' : 'No'}
            </dd>
          </dl>
        </Card>
      </div>

      {/* Text Tabs */}
      <div className="mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`border-b-2 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="mt-4">
          {textMap[activeTab] ? (
            <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-md bg-gray-50 p-4 text-sm text-gray-800">
              {textMap[activeTab]}
            </pre>
          ) : (
            <p className="rounded-md bg-gray-50 p-4 text-sm text-gray-400">
              No {tabs.find((t) => t.key === activeTab)?.label.toLowerCase()}{' '}
              available.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
