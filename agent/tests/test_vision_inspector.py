import unittest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool


class TestVisionInspector(unittest.TestCase):

    def setUp(self):
        self.search_tool = StockSearchTool()
        self.inspector = VisionInspectorTool()

    def test_evaluate_and_feedback_loop(self):
        """Thumbnail uygunluk puanlama ve iteratif arama testi."""
        scene_text = "Üslü sayılarda tabanlar aynı iken üsler toplanır."
        best_cand, logs = self.inspector.curate_best_visual(
            scene_text=scene_text,
            initial_keywords="math blackboard study",
            search_tool=self.search_tool,
            max_retries=2
        )
        self.assertIsNotNone(best_cand, "Uygun video adayı seçilemedi")
        self.assertGreater(len(logs), 0, "Arama ve denetim logları boş")
        self.assertIn("candidate_id", logs[0])
        self.assertIn("score", logs[0])


if __name__ == "__main__":
    unittest.main()
