"""Contract tests for fixed-width, versioned visual embedding persistence."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.infrastructure.ai.attribute_embedding_adapter import (
    EMBEDDING_DIMENSION, EMBEDDING_PREPROCESSING_VERSION, _prepare_image,
)
from app.infrastructure.persistence.vector_repository import VectorRepository


class VisualEmbeddingTests(unittest.TestCase):
    def test_preprocessing_composites_alpha_on_white_and_pads_to_square(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "crop.png"
            image = Image.new("RGBA", (100, 50), (255, 0, 0, 0))
            image.putpixel((50, 25), (0, 0, 255, 255))
            image.save(path)
            prepared = _prepare_image(path)
        self.assertEqual(prepared.size, (512, 512))
        self.assertEqual(prepared.mode, "RGB")
        self.assertEqual(prepared.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(EMBEDDING_PREPROCESSING_VERSION, "rgb-white-alpha-pad-512-bicubic-siglip-v1")

    def test_vector_repository_rejects_wrong_width_boolean_and_non_finite(self):
        repository = VectorRepository()
        valid = [0.0] * EMBEDDING_DIMENSION
        self.assertEqual(len(repository.validate(valid)), EMBEDDING_DIMENSION)
        self.assertTrue(repository.pgvector_literal(valid).startswith("[0,"))
        for invalid in ([0.0], [0.0] * (EMBEDDING_DIMENSION - 1) + [float("nan")], [False] * EMBEDDING_DIMENSION):
            with self.assertRaises(ValueError): repository.validate(invalid)
        GarmentAttributes({"embedding": valid}).validate_embedding(EMBEDDING_DIMENSION)


if __name__ == "__main__":
    unittest.main()
