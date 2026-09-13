"""Portable fullscreen host and native-screensaver frame worker."""
import argparse, json, os, random, signal, subprocess, sys, tempfile, time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QImage, QPainter, QWindow
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
import qt_backend as backend
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
config_path = Path(sys.executable).parent/'game.json' if getattr(sys,'frozen',False) else ROOT/'game.json'
CONFIG = json.loads((config_path if config_path.exists() else ROOT/'game.json').read_text())
if '--game' in sys.argv:
    index=sys.argv.index('--game')
    if index+1>=len(sys.argv) or sys.argv[index+1] not in ('asteroids','pong','snake'):
        raise SystemExit('--game requires asteroids, pong or snake')
    game=sys.argv[index+1]
    CONFIG={'game':game,'name':game.title()+'Screensaver'}
    del sys.argv[index:index+2]
GAME = CONFIG['game']
if GAME == 'asteroids':
    import engine
    # Reuse all game graphics with Qt rather than a system Cairo dependency.
    sys.modules['cairo'] = backend
    import render as art
elif GAME == 'snake':
    from snake import Arena
    from drawing import render_arena

class Simulation:
    def __init__(self, width, height):
        self.width,self.height=width,height
        self.last=self.started=time.monotonic();self.previous={};self.sparks=[];self.step_time=self.last
        self.process=None;self.temp=None
        if GAME=='asteroids': self.world=engine.World(random.randrange(2**31),width,height,start_in_warp=True)
        elif GAME=='snake': self.world=Arena(max(4,round(width/28)),max(4,round(height/56)*2),elapsed=0)
        else:
            self.temp=tempfile.TemporaryDirectory(prefix='retro-pong-');self.frame=Path(self.temp.name)/'frame.png'
            exe=ROOT/('pong.exe' if sys.platform=='win32' else 'pong')
            self.process=subprocess.Popen([str(exe),'--lock-frames',str(self.frame),'--width',str(width),'--height',str(height)],stdout=subprocess.DEVNULL)
    def draw(self,painter,width,height):
        now=time.monotonic()
        if GAME=='pong':
            painter.fillRect(0,0,width,height,Qt.GlobalColor.black)
            image=QImage(str(self.frame))
            if not image.isNull(): painter.drawImage(painter.viewport(),image)
        elif GAME=='asteroids':
            self.world.resize(width,height);self.world.advance(now-self.last)
            art.render(backend.Context(painter),self.world,width,height)
        else:
            if now-self.step_time>=1/12:
                self.previous={identity:(actor,list(actor.body)) for identity,actor in self.world.snakes.items()}
                self.sparks.extend((*food,now) for food in self.world.step(now-self.started));self.step_time=now
            self.sparks=[s for s in self.sparks if now-s[2]<.6]
            render_arena(backend.Context(painter),self.world,self.previous,min(1,(now-self.step_time)*12),width,height,now,self.sparks,elapsed=now-self.started,backend=backend)
        self.last=now
    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        if self.temp:self.temp.cleanup()

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].lower().split(':')[0] in ('/s','/c','/p'):
        mode,_,handle=argv[0].lower().partition(':')
        argv=[] if mode=='/s' else ['--configure'] if mode=='/c' else ['--embed',handle or (argv[1] if len(argv)>1 else '0')]
    elif not argv and sys.platform=='win32':argv=['--configure']
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',action='store_true');parser.add_argument('--configure',action='store_true')
    parser.add_argument('--embed',type=int,default=0);parser.add_argument('--frames');parser.add_argument('--duration',type=float,default=0)
    parser.add_argument('--width',type=int,default=1280);parser.add_argument('--height',type=int,default=720)
    args=parser.parse_args(argv)
    if args.width<100 or args.height<100 or args.width>16384 or args.height>16384 or args.duration<0:parser.error('Invalid dimensions or duration')
    if args.frames:os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    app=QApplication(sys.argv[:1])
    if args.configure:
        QMessageBox.information(None,CONFIG['name'],'Autonomous retro gameplay. Choose idle timeout and password protection in your operating system’s screensaver settings.');return 0
    if args.frames:
        scale=min(1,1280/max(args.width,args.height));w,h=round(args.width*scale),round(args.height*scale)
        sim=Simulation(w,h);output=Path(args.frames);started=time.monotonic()
        signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
        try:
            while not args.duration or time.monotonic()-started<args.duration:
                now=time.monotonic();image=QImage(w,h,QImage.Format.Format_ARGB32_Premultiplied)
                painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                sim.draw(painter,w,h);painter.end()
                temporary=output.with_suffix('.tmp.png')
                if not image.save(str(temporary),'PNG'):raise OSError('Cannot write frame')
                os.replace(temporary,output);app.processEvents();time.sleep(max(0,1/24-(time.monotonic()-now)))
        finally:sim.close()
        return 0
    class View(QWidget):
        def __init__(self,screen):
            super().__init__();self.started=time.monotonic();self.pointer=None
            self.setWindowTitle(CONFIG['name']);self.setMouseTracking(True)
            self.resize(960,600)
            if not args.preview and not args.embed:
                self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
                self.setGeometry(screen.geometry());self.setCursor(Qt.CursorShape.BlankCursor)
            self.sim=Simulation(max(100,self.width()),max(100,self.height()))
        def paintEvent(self,_):
            p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);self.sim.draw(p,self.width(),self.height());p.end()
        def keyPressEvent(self,event):
            if not args.embed and (not args.preview or event.key()==Qt.Key.Key_Escape):app.quit()
        def mousePressEvent(self,_):
            if not args.preview and not args.embed:app.quit()
        wheelEvent=mousePressEvent
        def mouseMoveEvent(self,event):
            point=event.globalPosition()
            if self.pointer is not None and (point-self.pointer).manhattanLength()>3 and time.monotonic()-self.started>1 and not args.preview and not args.embed:app.quit()
            self.pointer=point
    views=[View(s) for s in ([app.primaryScreen()] if args.preview or args.embed else app.screens())]
    foreign=None
    if args.embed:
        foreign=QWindow.fromWinId(args.embed)
        for view in views:
            view.winId();view.windowHandle().setParent(foreign);view.resize(foreign.size());view.show()
    else:
        for view in views:view.show()
    def tick():
        if args.embed and sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            rect=wintypes.RECT()
            if not ctypes.windll.user32.IsWindow(wintypes.HWND(args.embed)):
                app.quit();return
            if ctypes.windll.user32.GetClientRect(wintypes.HWND(args.embed),ctypes.byref(rect)):
                views[0].resize(max(1,rect.right),max(1,rect.bottom))
        for view in views:view.update()
    timer=QTimer();timer.timeout.connect(tick);timer.start(16)
    if args.duration:QTimer.singleShot(round(args.duration*1000),app.quit)
    app.screenAdded.connect(lambda *_:app.quit());app.screenRemoved.connect(lambda *_:app.quit())
    try:return app.exec()
    finally:
        for view in views:view.sim.close()

if __name__=='__main__':raise SystemExit(main())
