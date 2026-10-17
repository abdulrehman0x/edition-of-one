create extension if not exists vector;

-- Generic key/value table used by SupabaseStore.
create table if not exists kv (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

create table if not exists readers (
  id text primary key,
  name text not null,
  profile jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists sources (
  id text primary key,
  name text not null,
  url text not null,
  topics text[] default '{}',
  created_at timestamptz default now()
);

create table if not exists articles (
  id text primary key,
  source_id text references sources(id) on delete set null,
  title text not null,
  url text,
  body text,
  topics text[] default '{}',
  published_at timestamptz,
  embedding vector(384),
  created_at timestamptz default now()
);

create table if not exists editions (
  id text primary key,
  reader_id text references readers(id) on delete cascade,
  date date not null,
  payload jsonb not null,
  created_at timestamptz default now()
);

create table if not exists events (
  id bigserial primary key,
  reader_id text references readers(id) on delete cascade,
  article_id text,
  event_type text not null,
  value double precision default 1.0,
  created_at timestamptz default now()
);

create index if not exists articles_embedding_idx
  on articles using ivfflat (embedding vector_cosine_ops) with (lists = 100);
