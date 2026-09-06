-- Smart Wardrobe PostgreSQL + pgvector deployment schema.
-- Source: Figure 4.14 and Tables 4.4-4.5 in RSW_KhorHuaSheng_Project 1.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE app_user (
    user_id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    account_status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (account_status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE media_asset (
    media_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    media_type VARCHAR(50) NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    original_filename VARCHAR(255),
    mime_type VARCHAR(100) NOT NULL,
    byte_size BIGINT NOT NULL CHECK (byte_size > 0),
    width INTEGER,
    height INTEGER,
    status VARCHAR(30) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE user_preference (
    preference_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    preference_type VARCHAR(50) NOT NULL,
    preference_value JSONB NOT NULL,
    weight REAL,
    source VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE processing_job (
    job_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    source_media_id UUID NOT NULL REFERENCES media_asset(media_id),
    status VARCHAR(30) NOT NULL CHECK (status IN ('queued', 'processing', 'review_required', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE processing_item (
    processing_item_id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES processing_job(job_id),
    bounding_box JSONB NOT NULL,
    detected_category VARCHAR(50) NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    mask_media_id UUID REFERENCES media_asset(media_id),
    crop_media_id UUID REFERENCES media_asset(media_id),
    vtoff_media_id UUID REFERENCES media_asset(media_id),
    preferred_media_id UUID REFERENCES media_asset(media_id),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(768),
    review_status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'accepted', 'rejected', 'confirmed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE garment (
    garment_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    preferred_media_id UUID NOT NULL REFERENCES media_asset(media_id),
    processing_item_id UUID UNIQUE REFERENCES processing_item(processing_item_id),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    primary_colour VARCHAR(50),
    secondary_colour VARCHAR(50),
    pattern VARCHAR(50),
    style_tags JSONB,
    custom_tags JSONB,
    structural_scores JSONB,
    additional_attributes JSONB,
    embedding VECTOR(768),
    status VARCHAR(30) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'archived', 'deleted')),
    is_favourite BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE outfit (
    outfit_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    creation_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'archived', 'deleted')),
    is_favourite BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE outfit_item (
    outfit_id UUID NOT NULL REFERENCES outfit(outfit_id),
    garment_id UUID NOT NULL REFERENCES garment(garment_id),
    role VARCHAR(50) NOT NULL,
    item_order INTEGER NOT NULL CHECK (item_order > 0),
    PRIMARY KEY (outfit_id, garment_id)
);

CREATE TABLE nlp_chat (
    chat_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    request_text TEXT NOT NULL,
    interpreted_intent VARCHAR(100),
    extracted_entities JSONB,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE recommendation (
    recommendation_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    chat_id UUID REFERENCES nlp_chat(chat_id),
    recommendation_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    request_match_score REAL,
    compatibility_score REAL,
    preference_score REAL,
    total_score REAL
);

CREATE TABLE recommendation_item (
    recommendation_id UUID NOT NULL REFERENCES recommendation(recommendation_id),
    garment_id UUID NOT NULL REFERENCES garment(garment_id),
    garment_role VARCHAR(50) NOT NULL,
    item_order INTEGER NOT NULL CHECK (item_order > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (recommendation_id, garment_id)
);

CREATE TABLE person_image (
    person_image_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    media_id UUID NOT NULL REFERENCES media_asset(media_id),
    display_order INTEGER,
    status VARCHAR(30) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE visualisation (
    visualisation_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(user_id),
    person_image_id UUID NOT NULL REFERENCES person_image(person_image_id),
    outfit_id UUID REFERENCES outfit(outfit_id),
    recommendation_id UUID REFERENCES recommendation(recommendation_id),
    output_media_id UUID REFERENCES media_asset(media_id),
    source_type VARCHAR(30) NOT NULL CHECK (source_type IN ('outfit', 'recommendation')),
    configuration JSONB,
    model_version VARCHAR(100),
    status VARCHAR(30) NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CHECK ((source_type = 'outfit' AND outfit_id IS NOT NULL AND recommendation_id IS NULL)
        OR (source_type = 'recommendation' AND recommendation_id IS NOT NULL AND outfit_id IS NULL))
);

CREATE TABLE visualisation_item (
    visualisation_id UUID NOT NULL REFERENCES visualisation(visualisation_id),
    garment_id UUID NOT NULL REFERENCES garment(garment_id),
    source_media_id UUID NOT NULL REFERENCES media_asset(media_id),
    role VARCHAR(50) NOT NULL,
    item_order INTEGER NOT NULL CHECK (item_order > 0),
    PRIMARY KEY (visualisation_id, garment_id)
);

CREATE INDEX idx_media_asset_owner ON media_asset(user_id, status);
CREATE INDEX idx_processing_job_owner_status ON processing_job(user_id, status, created_at DESC);
CREATE INDEX idx_garment_owner_status ON garment(user_id, status, updated_at DESC);
CREATE INDEX idx_outfit_owner_status ON outfit(user_id, status, updated_at DESC);
CREATE INDEX idx_person_image_owner_status ON person_image(user_id, status);
CREATE INDEX idx_visualisation_owner_status ON visualisation(user_id, status, created_at DESC);
