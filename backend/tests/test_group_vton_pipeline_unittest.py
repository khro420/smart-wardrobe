import unittest
from io import BytesIO
from types import SimpleNamespace

from PIL import Image, ImageDraw

from app.infrastructure.ai.group_vton_pipeline import crop_for_person, feather_edit_mask, render_group
from app.infrastructure.ai.vton_preprocessing import encode_png


class FakeAdapter:
    def generate_for_person(self, plan, payload, garments, allowed_mask, callback):
        image = Image.new('RGB', allowed_mask.size, plan)
        image.putpixel((0, 0), (1, 2, 3))
        return SimpleNamespace(image=encode_png(image), output_kind='generated'), allowed_mask


class GroupPipelineTest(unittest.TestCase):
    def test_edge_crop_padding_preserves_coordinates(self):
        original = Image.new('RGB', (100, 160), 'white')
        crop = crop_for_person((0, 0, 100, 160), original.size)
        self.assertLess(crop.box[0], 0)
        self.assertEqual(crop.extract(original).size, (768, 1024))
        mask = Image.new('L', original.size)
        ImageDraw.Draw(mask).rectangle((0, 30, 40, 110), fill=255)
        output = crop.composite(original, Image.new('RGB', crop.size, 'red'), mask)
        self.assertEqual(output.getpixel((0, 50)), (255, 0, 0))
        self.assertEqual(output.getpixel((90, 50)), (255, 255, 255))

    def test_pipeline_with_padded_crop_keeps_nonperson_unchanged(self):
        original = Image.new('RGB', (100, 160), 'white')
        mask = Image.new('L', original.size)
        ImageDraw.Draw(mask).rectangle((0, 0, 60, 150), fill=255)
        person = SimpleNamespace(box=(0, 0, 100, 160), mask=mask)
        output = render_group(encode_png(original), [person], [(0, 'red', ())], FakeAdapter())
        with Image.open(BytesIO(output)) as result:
            self.assertEqual(result.getpixel((30, 80)), (255, 0, 0))
            self.assertEqual(result.getpixel((90, 80)), (255, 255, 255))

    def test_feather_never_edits_protected_pixels(self):
        edit = Image.new('L', (100, 100), 255)
        person = Image.new('L', (100, 100))
        ImageDraw.Draw(person).rectangle((20, 20, 79, 79), fill=255)
        mask = feather_edit_mask(edit, person)
        self.assertEqual(mask.getpixel((19, 50)), 0)
        self.assertLess(mask.getpixel((20, 50)), 255)
        self.assertEqual(mask.getpixel((50, 50)), 255)

    def test_change_outside_edit_mask_is_rejected(self):
        mask = Image.new('L', (240, 160))
        ImageDraw.Draw(mask).rectangle((20, 20, 70, 130), fill=255)
        people = [SimpleNamespace(box=(20, 20, 71, 131), mask=mask)]
        class UnchangedAdapter:
            def generate_for_person(self, plan, payload, garments, allowed_mask, callback):
                with Image.open(BytesIO(payload)) as image:
                    generated = image.convert('RGB')
                generated.putpixel((0, 0), (255, 0, 0))
                return SimpleNamespace(image=encode_png(generated), output_kind='generated'), allowed_mask
        with self.assertRaisesRegex(ValueError, 'usable preview'):
            render_group(encode_png(Image.new('RGB', (240, 160), 'white')), people, [(0, None, ())], UnchangedAdapter())

    def test_assignments_are_composited_only_over_each_person(self):
        original = Image.new('RGB', (240, 160), 'white')
        masks = [Image.new('L', original.size), Image.new('L', original.size)]
        ImageDraw.Draw(masks[0]).rectangle((20, 20, 70, 130), fill=255)
        ImageDraw.Draw(masks[1]).rectangle((160, 20, 210, 130), fill=255)
        people = [SimpleNamespace(box=(20, 20, 71, 131), mask=masks[0]), SimpleNamespace(box=(160, 20, 211, 131), mask=masks[1])]
        result = render_group(encode_png(original), people, [(0, 'red', ()), (1, 'blue', ())], FakeAdapter())
        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.getpixel((40, 80)), (255, 0, 0))
            self.assertEqual(image.getpixel((180, 80)), (0, 0, 255))
            self.assertEqual(image.getpixel((120, 80)), (255, 255, 255))

    def test_overlap_is_rejected(self):
        mask = Image.new('L', (240, 160), 255)
        people = [SimpleNamespace(box=(10, 10, 60, 130), mask=mask)] * 2
        with self.assertRaises(ValueError):
            render_group(encode_png(Image.new('RGB', (240, 160))), people, [(0, 'red', ())], FakeAdapter())

    def test_solid_model_output_is_rejected(self):
        mask = Image.new('L', (240, 160))
        ImageDraw.Draw(mask).rectangle((20, 20, 70, 130), fill=255)
        people = [SimpleNamespace(box=(20, 20, 71, 131), mask=mask)]
        class BlockedAdapter:
            def generate_for_person(self, plan, payload, garments, allowed_mask, callback):
                return SimpleNamespace(image=encode_png(Image.new('RGB', allowed_mask.size)), output_kind='generated'), allowed_mask
        with self.assertRaisesRegex(ValueError, 'usable preview'):
            render_group(encode_png(Image.new('RGB', (240, 160), 'white')), people, [(0, None, ())], BlockedAdapter())


if __name__ == '__main__':
    unittest.main()
