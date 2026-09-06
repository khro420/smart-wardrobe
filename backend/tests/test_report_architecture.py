"""Regression checks for report-mandated repository and schema structure."""

import unittest
import ast
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


class ReportArchitectureTests(unittest.TestCase):
    def test_garment_workflow_depends_on_ports_and_domain_not_concrete_adapters(self):
        for path in [*(BACKEND / "app/application/garment_processing").glob("*.py"),
                     BACKEND / "app/application/wardrobe/wardrobe_service.py"]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("app.infrastructure"), str(path))
        for path in (BACKEND / "app/domain").rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith(("app.infrastructure", "fastapi", "ultralytics", "torch", "sqlite3")), str(path))

    def test_single_backend_and_canonical_ml_locations(self):
        self.assertTrue((ROOT / "frontend").is_dir())
        self.assertTrue(BACKEND.is_dir())
        self.assertFalse((ROOT / "ai-services").exists())
        self.assertFalse((ROOT / "database").exists())
        self.assertFalse((ROOT / "runs").exists())
        for name in ("models", "datasets", "scripts", "runs", "migrations"):
            self.assertTrue((BACKEND / name).is_dir(), name)

    def test_figure_4_8_backend_packages_exist(self):
        app = BACKEND / "app"
        for name in ("api", "application", "domain", "infrastructure", "shared_contracts"):
            self.assertTrue((app / name).is_dir(), name)
        for path in (
            "api/garment_processing_routes.py", "api/wardrobe_routes.py", "api/visualisation_routes.py",
            "application/garment_processing", "application/wardrobe", "application/visualisation", "application/ports",
            "domain/entities", "domain/value_objects", "infrastructure/ai", "infrastructure/persistence", "infrastructure/media",
        ):
            self.assertTrue((app / path).exists(), path)
        self.assertFalse((app / "recommender").exists())
        self.assertFalse((app / "shared").exists())
        top_level_packages = {item.name for item in app.iterdir() if item.is_dir() and not item.name.startswith("__")}
        self.assertEqual(top_level_packages, {"api", "application", "domain", "infrastructure", "shared_contracts"})

    def test_report_integration_entities_have_executable_boundaries(self):
        app = BACKEND / "app"
        for path in (
            "api/recommendation_routes.py",
            "application/recommendation/recommendation_service.py",
            "shared_contracts/confirmed_garment_query.py",
            "shared_contracts/visualisation_gateway.py",
        ):
            self.assertTrue((app / path).is_file(), path)

    def test_postgresql_migration_covers_report_entities(self):
        migration = (BACKEND / "migrations" / "001_initial_schema.sql").read_text(encoding="utf-8").lower()
        for entity in (
            "app_user", "media_asset", "user_preference", "processing_job", "processing_item", "garment",
            "outfit", "outfit_item", "nlp_chat", "recommendation", "recommendation_item", "person_image",
            "visualisation", "visualisation_item",
        ):
            self.assertIn(f"create table {entity}", migration)
        self.assertIn("create extension if not exists vector", migration)
        self.assertEqual(migration.count("embedding vector(768)"), 2)

    def test_report_state_vocabulary_is_constrained_in_the_data_tier(self):
        migration = (BACKEND / "migrations" / "001_initial_schema.sql").read_text(encoding="utf-8").lower()
        for state in (
            "'queued'", "'processing'", "'review_required'", "'completed'", "'failed'", "'cancelled'",
            "'pending'", "'accepted'", "'rejected'", "'confirmed'", "'available'", "'archived'", "'deleted'",
            "'outfit'", "'recommendation'",
        ):
            self.assertIn(state, migration, state)


if __name__ == "__main__":
    unittest.main()
