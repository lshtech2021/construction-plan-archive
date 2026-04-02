import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listProjects } from '../api/projects';
import type { Project, PaginatedResponse } from '../api/types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Pagination } from '../components/ui/Pagination';

const PAGE_SIZE = 20;

export function ProjectListPage() {
  const [data, setData] = useState<PaginatedResponse<Project> | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listProjects(page, PAGE_SIZE)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Projects</h2>
        <Link to="/projects/new">
          <Button>+ New Project</Button>
        </Link>
      </div>

      {loading && <LoadingSpinner className="py-16" />}
      {error && (
        <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>
      )}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create your first project to get started."
          action={
            <Link to="/projects/new">
              <Button>+ New Project</Button>
            </Link>
          }
        />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((project) => (
              <Link key={project.id} to={`/projects/${project.id}`}>
                <Card className="h-full hover:border-blue-300">
                  <h3 className="mb-1 font-medium text-gray-900">
                    {project.name}
                  </h3>
                  {project.client && (
                    <p className="text-sm text-gray-500">
                      Client: {project.client}
                    </p>
                  )}
                  {project.location && (
                    <p className="text-sm text-gray-500">
                      Location: {project.location}
                    </p>
                  )}
                  {project.description && (
                    <p className="mt-2 line-clamp-2 text-sm text-gray-600">
                      {project.description}
                    </p>
                  )}
                  <p className="mt-3 text-xs text-gray-400">
                    {new Date(project.created_at).toLocaleDateString()}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
          <div className="mt-6">
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data.total}
              onPageChange={setPage}
            />
          </div>
        </>
      )}
    </div>
  );
}
