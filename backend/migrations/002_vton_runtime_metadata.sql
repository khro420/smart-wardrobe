BEGIN;
ALTER TABLE visualisation ADD COLUMN IF NOT EXISTS person_media_id UUID REFERENCES media_asset(media_id);
ALTER TABLE visualisation ADD COLUMN IF NOT EXISTS output_kind VARCHAR(30)
    CHECK (output_kind IN ('generated','development'));
ALTER TABLE visualisation ADD COLUMN IF NOT EXISTS metrics JSONB;
ALTER TABLE visualisation ADD COLUMN IF NOT EXISTS error_code VARCHAR(50);
ALTER TABLE visualisation_item ADD COLUMN IF NOT EXISTS category VARCHAR(50);
UPDATE visualisation SET output_kind='development', model_version='development-copy-v1'
WHERE output_kind IS NULL AND output_media_id IN (
    SELECT media_id FROM media_asset
    WHERE media_type='visualisation_output_development'
);
CREATE INDEX IF NOT EXISTS idx_visualisation_queue
    ON visualisation(status,created_at);
COMMIT;
