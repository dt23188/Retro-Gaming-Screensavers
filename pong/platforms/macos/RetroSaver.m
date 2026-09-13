#import <ScreenSaver/ScreenSaver.h>
#ifndef RETRO_CLASS
#define RETRO_CLASS RetroSaver
#endif
@interface RETRO_CLASS : ScreenSaverView
@property(nonatomic,strong) NSTask *worker;
@property(nonatomic,strong) NSString *framePath;
@property(nonatomic,strong) NSString *directory;
@property(nonatomic,strong) NSImage *image;
@property(nonatomic,strong) NSString *failure;
@end
@implementation RETRO_CLASS
- (instancetype)initWithFrame:(NSRect)frame isPreview:(BOOL)preview {
 self=[super initWithFrame:frame isPreview:preview];
 if(self){[self setAnimationTimeInterval:1.0/24.0];}return self;
}
- (void)startAnimation {
 [super startAnimation];if(self.worker)return;
 self.directory=[NSTemporaryDirectory() stringByAppendingPathComponent:[[NSUUID UUID] UUIDString]];
 [[NSFileManager defaultManager] createDirectoryAtPath:self.directory withIntermediateDirectories:YES attributes:nil error:nil];
 self.framePath=[self.directory stringByAppendingPathComponent:@"frame.png"];
 NSBundle *bundle=[NSBundle bundleForClass:[self class]];
 self.worker=[[NSTask alloc] init];self.worker.executableURL=[NSURL fileURLWithPath:[bundle objectForInfoDictionaryKey:@"WorkerExecutable"]];
 NSMutableArray *args=[[bundle objectForInfoDictionaryKey:@"WorkerArguments"] mutableCopy];
 CGFloat scale=self.window.backingScaleFactor?:1;
 [args addObjectsFromArray:@[@"--frames",self.framePath,@"--width",[NSString stringWithFormat:@"%d",MAX(100,(int)(self.bounds.size.width*scale))],@"--height",[NSString stringWithFormat:@"%d",MAX(100,(int)(self.bounds.size.height*scale))]]];
 self.worker.arguments=args;
 NSMutableDictionary *env=[[[NSProcessInfo processInfo] environment] mutableCopy];env[@"QT_QPA_PLATFORM"]=@"offscreen";self.worker.environment=env;
 self.worker.standardOutput=[NSFileHandle fileHandleWithNullDevice];self.worker.standardError=[NSFileHandle fileHandleWithNullDevice];
 NSError *error=nil;if(![self.worker launchAndReturnError:&error]){self.failure=error.localizedDescription;self.worker=nil;}
}
- (void)animateOneFrame {
 NSImage *next=[[NSImage alloc] initWithContentsOfFile:self.framePath];if(next)self.image=next;
 if(self.worker && !self.worker.running)self.failure=@"Renderer exited. Re-run the installer and check PORTABLE.md.";
 [self setNeedsDisplay:YES];
}
- (void)drawRect:(NSRect)rect {
 [[NSColor blackColor] setFill];NSRectFill(self.bounds);
 if(self.image)[self.image drawInRect:self.bounds fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1];
 else if(self.failure)[self.failure drawInRect:NSInsetRect(self.bounds,20,20) withAttributes:@{NSForegroundColorAttributeName:[NSColor whiteColor]}];
}
- (void)stopAnimation {
 if(self.worker.running)[self.worker terminate];
 self.worker=nil;self.image=nil;
 if(self.directory)[[NSFileManager defaultManager] removeItemAtPath:self.directory error:nil];
 [super stopAnimation];
}
@end
