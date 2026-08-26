import os
import unittest
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent.tools.diagram_generator import DiagramGenerator


class TestDiagramGenerator(unittest.TestCase):

    def setUp(self):
        self.sample_dir = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
        self.generator = DiagramGenerator(output_dir=self.sample_dir)

    def test_formula_card(self):
        file_path = self.generator.create_formula_card(
            title="Üslü Sayılarda Çarpma",
            formula="a^m · a^n = a^(m+n)",
            explanation="Tabanlar aynı ise üsler toplanır.",
            filename="test_formula_card.png"
        )
        self.assertTrue(os.path.exists(file_path))
        eval_result = DiagramGenerator.evaluate_diagram(file_path)
        self.assertTrue(eval_result["passed"])
        self.assertGreaterEqual(eval_result["score"], 7.0)

    def test_flowchart_diagram(self):
        file_path = self.generator.create_flowchart(
            title="Algoritma Akış Şeması",
            nodes=[
                {"label": "Girdi", "sub": "x, y sayıları"},
                {"label": "Toplama", "sub": "z = x + y"},
                {"label": "Çıktı", "sub": "Sonucu yazdır"}
            ],
            filename="test_flowchart.png"
        )
        self.assertTrue(os.path.exists(file_path))
        eval_result = DiagramGenerator.evaluate_diagram(file_path)
        self.assertTrue(eval_result["passed"])

    def test_comparison_matrix(self):
        file_path = self.generator.create_comparison_matrix(
            title="Mitoz vs Mayoz Bölünme",
            col1_title="Mitoz",
            col1_items=["Vücut hücrelerinde", "2 yeni hücre", "Kromozom sayısı sabit"],
            col2_title="Mayoz",
            col2_items=["Üreme ana hücresinde", "4 yeni hücre", "Kromozom sayısı yarıya iner"],
            filename="test_comparison.png"
        )
        self.assertTrue(os.path.exists(file_path))
        eval_result = DiagramGenerator.evaluate_diagram(file_path)
        self.assertTrue(eval_result["passed"])

    def test_timeline_diagram(self):
        file_path = self.generator.create_timeline_diagram(
            title="Milli Mücadele Kronolojisi",
            events=[
                {"date": "19 Mayıs 1919", "desc": "Samsun'a Çıkış"},
                {"date": "22 Haziran 1919", "desc": "Amasya Genelgesi"},
                {"date": "23 Nisan 1920", "desc": "TBMM Açılışı"},
                {"date": "29 Ekim 1923", "desc": "Cumhuriyetin İlanı"}
            ],
            filename="test_timeline.png"
        )
        self.assertTrue(os.path.exists(file_path))
        eval_result = DiagramGenerator.evaluate_diagram(file_path)
        self.assertTrue(eval_result["passed"])


if __name__ == "__main__":
    unittest.main()
