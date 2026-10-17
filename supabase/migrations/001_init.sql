create extension if not exists vector;

create table if not exists readers (
    id uuid primary key default gen_random_uuid(),
    display_name text not null default '',
    interests_text text not null default '',
    topic_weights jsonb not null default '{}'::jsonb,
    topic_stats jsonb not null default '{}'::jsonb,
    reading_minutes int not null default 15,
    region_bias real not null default 0.5,
    tone text not null default 'brief',
    watch_entities jsonb not null default '[]'::jsonb,
    centroid vector(384),
    created_at timestamptz not null default now()
);

create table if not exists sources (
    id serial primary key,
    name text not null,
    feed_url text not null unique,
    topic text not null default 'world',
    enabled boolean not null default true
);

create table if not exists articles (
    id text primary key,
    source_id integer references sources(id),
    url text not null unique,
    title text not null default '',
    body text not null default '',
    image_url text,
    published_at timestamptz,
    topic text not null default 'world',
    importance real not null default 0.5,
    brief text not null default '',
    cluster_id text,
    embedding vector(384),
    fetched_at timestamptz not null default now()
);

create table if not exists editions (
    id uuid primary key default gen_random_uuid(),
    reader_id uuid not null references readers(id) on delete cascade,
    edition_date date not null,
    doc jsonb not null,
    pdf_url text,
    audio_url text,
    unique (reader_id, edition_date)
);

create table if not exists events (
    id bigserial primary key,
    reader_id uuid not null references readers(id) on delete cascade,
    article_id text,
    edition_date date,
    type text not null check (type in ('impression','click','skip','dwell','thumb_up','thumb_down','save','pdf_open')),
    value real not null default 0.0,
    slot text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists articles_embedding_ivfflat_idx
    on articles using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists events_reader_created_idx
    on events (reader_id, created_at);
