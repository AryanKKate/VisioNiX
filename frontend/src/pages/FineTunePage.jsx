import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, LoaderCircle, RefreshCcw, Rocket, RotateCcw } from 'lucide-react';

import { useAuth } from '../hooks/useAuth';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

const initialForm = {
  model_name: '',
  task_type: 'classification',
  base_model: 'yolov8n',
  dataset_source: 'path',
  dataset_value: '',
  epochs: 10,
  batch_size: 16,
  image_size: 640,
  learning_rate: 0.001,
  validation_split: 0.2,
  quality_threshold: 0.6,
  auto_deploy: true,
  hf_space_slug: '',
  notes: '',
};

const runningStatuses = new Set(['queued', 'running', 'quality_check', 'deploying']);

export default function FineTunePage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [deployingJobId, setDeployingJobId] = useState('');
  const [result, setResult] = useState(null);

  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsError, setJobsError] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const datasetLabel = useMemo(() => {
    if (form.dataset_source === 'path') return 'Dataset Path';
    if (form.dataset_source === 'url') return 'Dataset URL';
    return 'Dataset Description';
  }, [form.dataset_source]);

  const hasRunningJobs = jobs.some((job) => runningStatuses.has((job.status || '').toLowerCase()));

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleReset = () => {
    setForm(initialForm);
    setResult(null);
  };

  const fetchJobs = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    setJobsLoading(true);
    setJobsError('');
    try {
      const response = await fetch(`${apiBaseUrl}/training/jobs`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Failed to load training jobs');
      }

      setJobs(data.jobs || []);
    } catch (error) {
      setJobsError(error.message || 'Failed to load training jobs');
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchJobs();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || !hasRunningJobs) return;
    const timer = setInterval(() => {
      fetchJobs();
    }, 8000);
    return () => clearInterval(timer);
  }, [isAuthenticated, hasRunningJobs]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setResult(null);

    const token = localStorage.getItem('token');
    if (!token) {
      setSubmitting(false);
      setResult({ type: 'error', message: 'Please login again.' });
      return;
    }

    const payload = {
      model_name: form.model_name.trim(),
      task_type: form.task_type,
      base_model: form.base_model.trim(),
      dataset_source: form.dataset_source,
      dataset_value: form.dataset_value.trim(),
      epochs: Number(form.epochs),
      batch_size: Number(form.batch_size),
      image_size: Number(form.image_size),
      learning_rate: Number(form.learning_rate),
      validation_split: Number(form.validation_split),
      quality_threshold: Number(form.quality_threshold),
      auto_deploy: Boolean(form.auto_deploy),
      hf_space_slug: form.hf_space_slug.trim(),
      notes: form.notes.trim(),
    };

    if (!payload.model_name || !payload.dataset_value) {
      setSubmitting(false);
      setResult({ type: 'error', message: 'Model name and dataset details are required.' });
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/training/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || 'Failed to submit fine-tuning job');
      }

      setResult({
        type: 'success',
        message: 'Fine-tuning job submitted and worker started.',
        details: data,
      });
      await fetchJobs();
    } catch (error) {
      setResult({ type: 'error', message: error.message || 'Submission failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeploy = async (jobId) => {
    const token = localStorage.getItem('token');
    if (!token) {
      setResult({ type: 'error', message: 'Please login again.' });
      return;
    }

    setDeployingJobId(jobId);
    setResult(null);
    try {
      const response = await fetch(`${apiBaseUrl}/training/jobs/${jobId}/deploy`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Deployment failed');
      }

      setResult({
        type: 'success',
        message: 'Deployment started/completed successfully.',
        details: data,
      });
      await fetchJobs();
    } catch (error) {
      setResult({ type: 'error', message: error.message || 'Deployment failed.' });
    } finally {
      setDeployingJobId('');
    }
  };

  return (
    <div className="min-h-screen bg-primary text-light">
      <div className="bg-secondary border-b border-border sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 text-light hover:text-text-secondary transition-colors font-medium"
          >
            <ArrowLeft size={18} />
            Back to Chat
          </button>
          <h1 className="text-xl font-semibold">Fine-Tuning + Deploy</h1>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <form onSubmit={handleSubmit} className="bg-secondary border border-border rounded-xl p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Model Name</label>
              <input
                value={form.model_name}
                onChange={(e) => handleChange('model_name', e.target.value)}
                placeholder="pneumonia-v1"
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Task Type</label>
              <select
                value={form.task_type}
                onChange={(e) => handleChange('task_type', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              >
                <option value="classification">Classification</option>
                <option value="detection">Detection</option>
                <option value="segmentation">Segmentation</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Base Model</label>
              <input
                value={form.base_model}
                onChange={(e) => handleChange('base_model', e.target.value)}
                placeholder="yolov8n"
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Dataset Source</label>
              <select
                value={form.dataset_source}
                onChange={(e) => handleChange('dataset_source', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              >
                <option value="path">Local Path</option>
                <option value="url">URL (metadata only)</option>
                <option value="manual">Manual Notes</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm mb-2 text-text-secondary">{datasetLabel}</label>
              <input
                value={form.dataset_value}
                onChange={(e) => handleChange('dataset_value', e.target.value)}
                placeholder={form.dataset_source === 'path' ? 'data/rsna/train' : 'https://...'}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Epochs</label>
              <input
                type="number"
                min="1"
                value={form.epochs}
                onChange={(e) => handleChange('epochs', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Batch Size</label>
              <input
                type="number"
                min="1"
                value={form.batch_size}
                onChange={(e) => handleChange('batch_size', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Image Size</label>
              <input
                type="number"
                min="64"
                step="32"
                value={form.image_size}
                onChange={(e) => handleChange('image_size', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Learning Rate</label>
              <input
                type="number"
                min="0"
                step="0.0001"
                value={form.learning_rate}
                onChange={(e) => handleChange('learning_rate', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Validation Split</label>
              <input
                type="number"
                min="0.05"
                max="0.5"
                step="0.01"
                value={form.validation_split}
                onChange={(e) => handleChange('validation_split', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">Quality Threshold</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={form.quality_threshold}
                onChange={(e) => handleChange('quality_threshold', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm mb-2 text-text-secondary">HF Space Slug (optional)</label>
              <input
                value={form.hf_space_slug}
                onChange={(e) => handleChange('hf_space_slug', e.target.value)}
                placeholder="AryanKKate/Model"
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm mb-2 text-text-secondary">Notes</label>
              <textarea
                rows="3"
                value={form.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                placeholder="Any training-specific notes..."
                className="w-full px-3 py-2 rounded-lg bg-primary border border-border focus:outline-none resize-none"
              />
            </div>
            <div className="md:col-span-2 flex items-center gap-3">
              <input
                id="auto_deploy"
                type="checkbox"
                checked={form.auto_deploy}
                onChange={(e) => handleChange('auto_deploy', e.target.checked)}
              />
              <label htmlFor="auto_deploy" className="text-sm text-text-secondary">
                Auto deploy to Hugging Face Space after training
              </label>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-light hover:bg-hover disabled:opacity-50"
            >
              {submitting ? <LoaderCircle size={16} className="animate-spin" /> : <Rocket size={16} />}
              {submitting ? 'Submitting...' : 'Submit Fine-Tune Job'}
            </button>
            <button
              type="button"
              onClick={handleReset}
              disabled={submitting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-hover disabled:opacity-50"
            >
              <RotateCcw size={16} />
              Reset
            </button>
            <button
              type="button"
              onClick={fetchJobs}
              disabled={jobsLoading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-hover disabled:opacity-50"
            >
              <RefreshCcw size={16} className={jobsLoading ? 'animate-spin' : ''} />
              Refresh Jobs
            </button>
          </div>
        </form>

        {result && (
          <div
            className={`rounded-lg border p-4 text-sm ${
              result.type === 'success'
                ? 'border-green-600 bg-green-900/30 text-green-200'
                : result.type === 'warning'
                ? 'border-yellow-600 bg-yellow-900/30 text-yellow-200'
                : 'border-red-600 bg-red-900/30 text-red-200'
            }`}
          >
            <p className="font-semibold mb-1">{result.message}</p>
            {result.details && (
              <pre className="mt-2 text-xs overflow-x-auto whitespace-pre-wrap">{JSON.stringify(result.details, null, 2)}</pre>
            )}
          </div>
        )}

        <div className="bg-secondary border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Training Jobs</h2>

          {jobsError && <p className="text-red-300 text-sm mb-4">{jobsError}</p>}

          {jobs.length === 0 ? (
            <p className="text-text-secondary text-sm">No jobs yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-secondary border-b border-border">
                    <th className="py-2 pr-3">Model</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Metric</th>
                    <th className="py-2 pr-3">HF Space</th>
                    <th className="py-2 pr-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => {
                    const canDeploy =
                      !job.hf_space_url &&
                      ['trained', 'ready_for_deploy', 'completed'].includes((job.status || '').toLowerCase());
                    return (
                      <tr key={job.id} className="border-b border-border align-top">
                        <td className="py-2 pr-3">
                          <div className="font-medium">{job.model_name}</div>
                          <div className="text-xs text-text-secondary">{job.id}</div>
                        </td>
                        <td className="py-2 pr-3">
                          <div className="font-medium">{job.status}</div>
                          <div className="text-xs text-text-secondary">{job.status_message}</div>
                        </td>
                        <td className="py-2 pr-3">
                          {typeof job.best_metric === 'number' ? job.best_metric.toFixed(4) : '-'}
                        </td>
                        <td className="py-2 pr-3 break-all">
                          {job.hf_space_url ? (
                            <a
                              href={job.hf_space_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan-300 hover:underline"
                            >
                              {job.hf_space_url}
                            </a>
                          ) : (
                            <span className="text-text-secondary">-</span>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {canDeploy ? (
                            <button
                              onClick={() => handleDeploy(job.id)}
                              disabled={deployingJobId === job.id}
                              className="px-3 py-1 rounded bg-surface-light hover:bg-hover disabled:opacity-50"
                            >
                              {deployingJobId === job.id ? 'Deploying...' : 'Deploy'}
                            </button>
                          ) : (
                            <span className="text-text-secondary">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
