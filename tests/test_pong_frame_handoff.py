"""Regression tests for the shared host's frame replacement handoff."""
from pathlib import Path
import os,sys,tempfile,unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'asteroids/src'))
import retro_portable as host
from PySide6.QtGui import QColor,QImage,QPainter
from PySide6.QtWidgets import QApplication

class FrameHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.sim=host.Simulation.__new__(host.Simulation)
        self.sim.frame=Path(self.directory.name)/'frame.bmp'
        self.sim.last_frame=QImage()
    def paint(self):
        canvas=QImage(160,100,QImage.Format.Format_RGB32)
        canvas.fill(QColor('magenta'))
        painter=QPainter(canvas)
        try:
            with patch.object(host,'GAME','pong'): self.sim.draw(painter,160,100)
        finally: painter.end()
        return canvas
    def publish(self,color):
        image=QImage(160,100,QImage.Format.Format_RGB32)
        image.fill(QColor(color))
        self.assertTrue(image.save(str(self.sim.frame),'BMP'))
    def test_missing_first_frame_paints_black(self):
        self.assertEqual(self.paint().pixelColor(80,50),QColor('black'))
    def test_replacement_failure_retains_complete_frame(self):
        self.publish('cyan')
        expected=self.paint()
        self.sim.frame.write_bytes(b'incomplete bitmap')
        self.assertEqual(self.paint(),expected)
        self.sim.frame.unlink()
        self.assertEqual(self.paint(),expected)
    def test_next_complete_frame_replaces_cached_frame(self):
        self.publish('cyan');self.paint()
        self.publish('yellow')
        self.assertEqual(self.paint().pixelColor(80,50),QColor('yellow'))

if __name__=='__main__':unittest.main()
