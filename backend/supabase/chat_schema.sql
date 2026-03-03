-- Chat room and message schema for Supabase (PostgreSQL)
-- Run this in the Supabase SQL editor.

create extension if not exists pgcrypto;

create table if not exists public.chat_rooms (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'New Chat',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  room_id uuid not null references public.chat_rooms (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  image_name text,
  image_mime_type text,
  image_data text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_chat_rooms_user_id_updated_at
  on public.chat_rooms (user_id, updated_at desc);

create index if not exists idx_chat_messages_room_id_created_at
  on public.chat_messages (room_id, created_at asc);

alter table public.chat_rooms enable row level security;
alter table public.chat_messages enable row level security;

create policy if not exists "users_can_manage_own_rooms"
  on public.chat_rooms
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy if not exists "users_can_manage_messages_in_own_rooms"
  on public.chat_messages
  for all
  using (
    exists (
      select 1
      from public.chat_rooms r
      where r.id = chat_messages.room_id
        and r.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.chat_rooms r
      where r.id = chat_messages.room_id
        and r.user_id = auth.uid()
    )
  );
