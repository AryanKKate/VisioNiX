-- Training jobs schema for VisioNiX fine-tuning + HF deployment pipeline.
-- Run in Supabase SQL editor for persistent storage.
-- If not applied, backend will use local fallback: backend/logs/training_jobs.json

create extension if not exists pgcrypto;

create table if not exists public.training_jobs (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,

  model_name text not null,
  task_type text not null check (task_type in ('classification', 'detection', 'segmentation')),
  base_model text not null,
  dataset_source text not null check (dataset_source in ('path', 'url', 'manual')),
  dataset_value text not null,

  config_json jsonb not null default '{}'::jsonb,
  auto_deploy boolean not null default false,
  hf_space_slug text,
  notes text,

  status text not null default 'queued',
  status_message text,
  artifact_path text,
  metrics_json jsonb,
  best_metric double precision,
  quality_gate_passed boolean,
  model_id uuid,
  hf_space_url text,
  error text,
  logs jsonb not null default '[]'::jsonb,

  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_training_jobs_user_created
  on public.training_jobs (user_id, created_at desc);

create index if not exists idx_training_jobs_status
  on public.training_jobs (status);

alter table public.training_jobs enable row level security;

drop policy if exists "users_can_manage_own_training_jobs" on public.training_jobs;

create policy "users_can_manage_own_training_jobs"
  on public.training_jobs
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Optional model registry columns used by training/deployment pipeline.
-- Safe on projects where public.models already exists with different shape.
alter table if exists public.models
  add column if not exists hf_space_url text;

alter table if exists public.models
  add column if not exists task_type text;

alter table if exists public.models
  add column if not exists status text;

alter table if exists public.models
  add column if not exists updated_at timestamptz;
