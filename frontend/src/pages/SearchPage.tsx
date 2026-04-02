import { useState } from 'react';
import { Link } from 'react-router-dom';
import { search } from '../api/search';
import type { SearchResult } from '../api/types';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';

const SEARCH_TYPES = [
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'semantic', label: 'Semantic' },
  { value: 'keyword', label: 'Keyword' },
];

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState<'hybrid' | 'semantic' | 'keyword'>('hybrid');
  const [discipline, setDiscipline] = useState('');
  const [sheetType, setSheetType] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await search({
        query: query.trim(),
        search_type: searchType,
        discipline: discipline || undefined,
        sheet_type: sheetType || undefined,
        limit: 20,
      });
      setResults(res.results);
      setTotal(res.total);
      setSearched(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-6 text-xl font-semibold text-gray-900">Search</h2>

      <Card className="mb-6">
        <form onSubmit={handleSearch} className="flex flex-col gap-4">
          <Input
            label="Search Query"
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. foundation detail, electrical panel..."
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Select
              label="Search Type"
              id="search-type"
              value={searchType}
              onChange={(e) =>
                setSearchType(
                  e.target.value as 'hybrid' | 'semantic' | 'keyword',
                )
              }
              options={SEARCH_TYPES}
            />
            <Input
              label="Discipline Filter"
              id="discipline"
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
              placeholder="e.g. structural"
            />
            <Input
              label="Sheet Type Filter"
              id="sheet-type"
              value={sheetType}
              onChange={(e) => setSheetType(e.target.value)}
              placeholder="e.g. plan"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" loading={loading}>
              Search
            </Button>
          </div>
        </form>
      </Card>

      {loading && <LoadingSpinner className="py-8" />}
      {error && (
        <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>
      )}
      {!loading && searched && results.length === 0 && (
        <EmptyState
          title="No results found"
          description="Try adjusting your query or filters."
        />
      )}
      {!loading && results.length > 0 && (
        <div>
          <p className="mb-3 text-sm text-gray-500">
            {total} result{total !== 1 ? 's' : ''} found
          </p>
          <div className="flex flex-col gap-3">
            {results.map((result) => (
              <Link key={result.sheet.id} to={`/sheets/${result.sheet.id}`}>
                <Card className="hover:border-blue-300">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="font-medium text-gray-900">
                          {result.sheet.sheet_number ??
                            `Page ${result.sheet.page_number}`}
                        </span>
                        <Badge color="blue">{result.sheet.discipline}</Badge>
                        <Badge color="gray">{result.sheet.sheet_type}</Badge>
                      </div>
                      {result.sheet.sheet_title && (
                        <p className="text-sm text-gray-600">
                          {result.sheet.sheet_title}
                        </p>
                      )}
                      {result.highlight && (
                        <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                          {result.highlight}
                        </p>
                      )}
                    </div>
                    <span className="shrink-0 text-xs text-gray-400">
                      Score: {result.score.toFixed(3)}
                    </span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
