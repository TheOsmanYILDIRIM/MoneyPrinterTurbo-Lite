import unittest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent.tools.stock_search import StockSearchTool


class TestStockSearch(unittest.TestCase):

    def setUp(self):
        self.tool = StockSearchTool()

    def test_search_thumbnails_structure(self):
        """Thumbnail arama sonucunun hafif ve doğru yapıda olduğunu doğrular."""
        results = self.tool.search_pexels_thumbnails("blackboard math teacher", per_page=3)
        self.assertGreater(len(results), 0, "Arama sonucu boş döndü")
        first = results[0]
        self.assertIn("provider", first)
        self.assertIn("video_id", first)
        self.assertIn("thumbnail_url", first)
        self.assertIn("available_files", first)


if __name__ == "__main__":
    unittest.main()
