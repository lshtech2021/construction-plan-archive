import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getProject, deleteProject } from '../api/projects';
import { listDocuments, uploadDocument } from '../api/documents';
import type { Project, Document } from '../api/types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { FileUpload } from '../components/ui/FileUpload';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Modal } from '../components/ui/Modal';
import { StatusBadge } from '../components/ui/StatusBadge';

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(id), listDocuments(id)])
      .then(([proj, docs]) => {
        setProject(proj);
        setDocuments(docs.items);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleUpload = async (file: File) => {
    if (!id) return;
    setUploading(true);
    setUploadError(null);
    try {
      const doc = await uploadDocument(id, file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await deleteProject(id);
      navigate('/');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed');
      setShowDeleteModal(false);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <LoadingSpinner className="py-16" />;
  if (error)
    return (
      <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>
    );
  if (!project) return null;

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {project.name}
          </h2>
          {project.client && (
            <p className="text-sm text-gray-500">Client: {project.client}</p>
          )}
          {project.location && (
            <p className="text-sm text-gray-500">
              Location: {project.location}
            </p>
          )}
          {project.description && (
            <p className="mt-1 text-sm text-gray-600">{project.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link to={`/projects/${id}/edit`}>
            <Button variant="secondary" size="sm">
              Edit
            </Button>
          </Link>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Upload */}
      <div className="mb-6">
        <h3 className="mb-3 text-sm font-medium text-gray-700">
          Upload Document
        </h3>
        <FileUpload onFile={handleUpload} uploading={uploading} />
        {uploadError && (
          <p className="mt-2 text-sm text-red-600">{uploadError}</p>
        )}
      </div>

      {/* Documents */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-gray-700">
          Documents ({documents.length})
        </h3>
        {documents.length === 0 ? (
          <EmptyState
            title="No documents yet"
            description="Upload a PDF to start processing."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {documents.map((doc) => (
              <Link key={doc.id} to={`/documents/${doc.id}`}>
                <Card className="hover:border-blue-300">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {doc.original_filename}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(doc.file_size_bytes / 1024).toFixed(1)} KB
                        {doc.page_count != null
                          ? ` · ${doc.page_count} pages`
                          : ''}
                      </p>
                    </div>
                    <StatusBadge status={doc.processing_status} />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      <Modal
        open={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Project"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setShowDeleteModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleting}
              onClick={handleDelete}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{' '}
          <strong>{project.name}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
