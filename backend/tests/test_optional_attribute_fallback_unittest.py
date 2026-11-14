import unittest
from unittest.mock import Mock

from app.infrastructure.ai.attribute_embedding_adapter import OptionalAttributeAdapter
from app.domain.value_objects.garment_attributes import GarmentAttributes


class OptionalAttributeTest(unittest.TestCase):
    def test_failed_optional_model_keeps_processing_with_explicit_unavailable_status(self):
        model = Mock()
        model.extract.side_effect = FileNotFoundError('missing model')
        with self.assertLogs('app.infrastructure.ai.attribute_embedding_adapter', level='ERROR'):
            result = OptionalAttributeAdapter(model).extract('garment.png')
        self.assertIsNone(result.values['embedding'])
        self.assertEqual(result.values['embedding_status'], 'unavailable')

    def test_successful_model_result_is_preserved(self):
        expected = GarmentAttributes({'embedding': [1.0], 'embedding_status': 'available'})
        model = Mock()
        model.extract.return_value = expected
        self.assertIs(OptionalAttributeAdapter(model).extract('garment.png'), expected)

    def test_missing_optional_assets_do_not_discard_a_valid_processing_job(self):
        # The optional-model loader fails before reading the garment on a fresh
        # teammate installation; that must still yield an explicit fallback.
        from app.infrastructure.ai.attribute_embedding_adapter import SiglipEmbeddingAdapter
        from pathlib import Path
        adapter = OptionalAttributeAdapter(SiglipEmbeddingAdapter(Path('missing-optional-model'), 'cpu'))
        with self.assertLogs('app.infrastructure.ai.attribute_embedding_adapter', level='ERROR'):
            result = adapter.extract('garment.png')
        self.assertEqual(result.values['embedding_status'], 'unavailable')
        self.assertIsNone(result.values['embedding'])
