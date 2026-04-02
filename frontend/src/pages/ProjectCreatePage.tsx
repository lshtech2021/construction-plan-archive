import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProject } from '../api/projects';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { TextArea } from '../components/ui/TextArea';

export function ProjectCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    client: '',
    location: '',
    description: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const project = await createProject({
        name: form.name.trim(),
        client: form.client.trim() || undefined,
        location: form.location.trim() || undefined,
        description: form.description.trim() || undefined,
      });
      navigate(`/projects/${project.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <h2 className="mb-6 text-xl font-semibold text-gray-900">
        New Project
      </h2>
      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Project Name *"
            id="name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Office Tower A"
            required
          />
          <Input
            label="Client"
            id="client"
            value={form.client}
            onChange={(e) => setForm({ ...form, client: e.target.value })}
            placeholder="Client name"
          />
          <Input
            label="Location"
            id="location"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
            placeholder="Site location"
          />
          <TextArea
            label="Description"
            id="description"
            value={form.description}
            onChange={(e) =>
              setForm({ ...form, description: e.target.value })
            }
            placeholder="Brief description of the project"
            rows={3}
          />
          {error && (
            <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(-1)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              Create Project
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
