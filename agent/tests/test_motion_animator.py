import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from agent.tools.motion_animator import MotionAnimator


class TestMotionAnimator(unittest.TestCase):

    def setUp(self):
        self.sample_dir = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
        self.animator = MotionAnimator(output_dir=self.sample_dir)

    def test_3d_rotating_cube(self):
        """3D dönen küp animasyonu üretimi ve dosya doğrulaması."""
        path = self.animator.render_3d_rotating_cube(
            title="3D Geometri / Hacim",
            formula="V = a³",
            duration_sec=2.5,
            fps=20,
            filename="dynamic_3d_cube.gif"
        )
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

    def test_progressive_steps_reveal(self):
        """Sırayla beliren adımlar animasyonu üretimi."""
        path = self.animator.render_progressive_steps_reveal(
            title="Kareköklü Sayı Sadeleştirme",
            steps=[
                "1. Tam kare çarpanı bul",
                "2. Kök dışına çıkar",
                "3. Kalan terimi sadeleştir"
            ],
            duration_sec=3.0,
            fps=20,
            filename="dynamic_steps_reveal.gif"
        )
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

    def test_full_demo_video(self):
        """480p animasyonlu video derleme testi."""
        cube_path = os.path.join(self.sample_dir, "dynamic_3d_cube.gif")
        video_path = self.animator.render_demo_video(
            script_text="Küpün hacmi bir ayrıtının küpü alınarak hesaplanır.",
            overlay_anim_path=cube_path,
            filename="sample_animated_kpss_lesson.mp4"
        )
        self.assertTrue(os.path.exists(video_path))
        self.assertGreater(os.path.getsize(video_path), 5000)


if __name__ == "__main__":
    unittest.main()
