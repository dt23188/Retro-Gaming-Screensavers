from pathlib import Path
import os, sys, unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'asteroids/src'))
import retro_portable as host
from PySide6.QtGui import QImage,QPainter
from PySide6.QtWidgets import QApplication
from engine import World, Saucer, Vec, CorePart

class PortableRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def frame(self,w,width,height):
        w.resize(width,height)
        image=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied)
        painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        host.art.render(host.backend.Context(painter),w,width,height);painter.end()
        self.assertFalse(image.isNull())
        pixels=bytes(image.constBits())
        self.assertGreater(sum(pixels[i:i+3]!=b'\0\0\0' for i in range(0,len(pixels),4)),100)
        return image
    def test_all_fleets_pickups_and_shield_render(self):
        for kind in ('ring','raider','marauder'):
            w=World(1979,640,360);w.time=2;w.ship.invulnerable=0;w.shield_remaining=25
            w.saucer=Saucer(Vec(70,40),Vec(),False,kind=kind)
            w.parts=[CorePart(Vec(-70,-50),born=0,kind=k) for k in ('core','shield','missile','blast')]
            self.frame(w,640,360)
    def test_warp_frames_fit_portrait_and_ultrawide(self):
        w=World(1979);w.core_parts=5;w.start_warp()
        for _ in range(30):w.advance(.25)
        for width,height in ((360,640),(1024,288)):
            self.frame(w,width,height)
    def test_radial_blast_renders(self):
        w=World(42);w.blast_charges=1;w.activate_blast();w.update_blast(.3)
        self.frame(w,640,360)

    def test_ship_destruction_overlay_renders(self):
        w=World(42);w.ship.invulnerable=0;w.destroy_ship()
        self.frame(w,640,360)

if __name__=='__main__':unittest.main()
