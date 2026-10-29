-- Deployment counterpart only; the running prototype uses SQLite.
BEGIN;
LOCK TABLE recommendation, recommendation_item, nlp_chat IN SHARE ROW EXCLUSIVE MODE;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM recommendation WHERE chat_id IS NOT NULL GROUP BY chat_id HAVING count(*)>1)
     OR EXISTS (SELECT 1 FROM recommendation_item GROUP BY recommendation_id,item_order HAVING count(*)>1)
     OR EXISTS (SELECT 1 FROM recommendation r JOIN nlp_chat c USING(chat_id) WHERE r.user_id<>c.user_id)
     OR EXISTS (SELECT 1 FROM recommendation_item i JOIN recommendation r USING(recommendation_id)
                JOIN garment g USING(garment_id) WHERE r.user_id<>g.user_id) THEN
    RAISE EXCEPTION 'Historical recommendation integrity conflict; no automatic repair';
  END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS rec_one_chat ON recommendation(chat_id) WHERE chat_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS rec_item_order ON recommendation_item(recommendation_id,item_order);
CREATE TABLE IF NOT EXISTS recommendation_metadata (
  recommendation_id UUID PRIMARY KEY REFERENCES recommendation(recommendation_id),
  provenance JSONB NOT NULL, score_metadata JSONB
);
CREATE TABLE IF NOT EXISTS recommendation_item_snapshot (
  recommendation_id UUID NOT NULL, garment_id UUID NOT NULL, display_snapshot JSONB NOT NULL,
  PRIMARY KEY(recommendation_id,garment_id),
  FOREIGN KEY(recommendation_id,garment_id) REFERENCES recommendation_item(recommendation_id,garment_id)
);
CREATE TABLE IF NOT EXISTS recommendation_submission (
  user_id UUID NOT NULL REFERENCES app_user(user_id),
  operation TEXT NOT NULL CHECK(operation IN ('homepage','assistant')),
  submission_key TEXT NOT NULL, fingerprint TEXT NOT NULL,
  recommendation_id UUID NOT NULL UNIQUE REFERENCES recommendation(recommendation_id),
  PRIMARY KEY(user_id,operation,submission_key)
);
CREATE OR REPLACE FUNCTION validate_recommendation_submission() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS(SELECT 1 FROM recommendation r LEFT JOIN nlp_chat c USING(chat_id)
     WHERE r.recommendation_id=NEW.recommendation_id AND r.user_id=NEW.user_id
     AND ((NEW.operation='homepage' AND r.chat_id IS NULL) OR
          (NEW.operation='assistant' AND c.user_id=NEW.user_id AND c.status='completed')))
     OR EXISTS(SELECT 1 FROM recommendation_item i JOIN garment g USING(garment_id)
       WHERE i.recommendation_id=NEW.recommendation_id AND g.user_id<>NEW.user_id) THEN
    RAISE EXCEPTION 'Recommendation ownership/reference violation';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS recommendation_submission_owner ON recommendation_submission;
CREATE TRIGGER recommendation_submission_owner BEFORE INSERT OR UPDATE ON recommendation_submission
FOR EACH ROW EXECUTE FUNCTION validate_recommendation_submission();
COMMIT;
