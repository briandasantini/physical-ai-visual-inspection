import unittest

import numpy as np
from PIL import Image

from visual_inspection.vision import build_contour_diff


class ContourDiffTests(unittest.TestCase):
    def test_identical_images_have_no_regions(self):
        image = Image.fromarray(np.zeros((400, 400, 3), dtype=np.uint8))

        result = build_contour_diff(image, image)

        self.assertEqual(result.regions, ())
        self.assertEqual(result.changed_pixel_ratio, 0.0)

    def test_large_change_creates_region(self):
        reference = np.zeros((400, 400, 3), dtype=np.uint8)
        live = reference.copy()
        live[100:220, 120:260] = 255

        result = build_contour_diff(Image.fromarray(reference), Image.fromarray(live))

        self.assertGreaterEqual(len(result.regions), 1)
        self.assertGreater(result.regions[0].area, 3000)
        self.assertEqual(result.image.size, (400, 400))

    def test_live_image_is_resized_to_reference(self):
        reference = Image.fromarray(np.zeros((300, 500, 3), dtype=np.uint8))
        live = Image.fromarray(np.zeros((150, 250, 3), dtype=np.uint8))

        result = build_contour_diff(reference, live)

        self.assertEqual(result.image.size, (500, 300))


if __name__ == "__main__":
    unittest.main()
