import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('screensaver_session',
    Path(__file__).resolve().parents[1] / 'packaging/omarchy/retro-screensaver-session.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


class PointerTests(unittest.TestCase):
    def monitor(self, **changes):
        result = dict(name='DP-1', x=200, y=2160, width=3440, height=1440, scale=1, transform=0)
        result.update(changes)
        return result

    def test_capture_monitor_containing_pointer_not_focused_monitor(self):
        monitors = [self.monitor(name='DP-2', x=0, y=0, width=3840, height=2160, focused=True),
                    self.monitor(focused=False)]
        with patch.object(session, 'hypr_json', side_effect=[dict(x=1060, y=2520), monitors]):
            self.assertEqual(session.capture_pointer(), ('DP-1', .25, .25))

    def test_restores_exact_point_after_focus_warp(self):
        with patch.object(session, 'hypr_json', return_value=[self.monitor()]), \
                patch.object(session, 'query', side_effect=['false', 'ok']) as query:
            session.restore_pointer(('DP-1', .25, .25))
        self.assertEqual(query.call_args.args,
            ('hyprctl', 'dispatch', 'hl.dsp.cursor.move({ x = 1060, y = 2520 })'))

    def test_scaled_rotated_monitor_repositioning(self):
        monitor = self.monitor(x=-1080, y=0, width=3840, height=2160, scale=2, transform=1)
        with patch.object(session, 'hypr_json', return_value=[monitor]), \
                patch.object(session, 'query', side_effect=['false', 'ok']) as query:
            session.restore_pointer(('DP-1', .5, .25))
        self.assertIn('x = -540, y = 480', query.call_args.args[-1])

    def test_skip_disconnected_monitor_and_locked_session(self):
        for lock, monitors in [('true', [self.monitor()]), (None, [self.monitor()]), ('false', [])]:
            with patch.object(session, 'hypr_json', return_value=monitors), \
                    patch.object(session, 'query', return_value=lock) as query:
                session.restore_pointer(('DP-1', .25, .25))
                self.assertEqual(query.call_count, 1)

    def test_legacy_dispatch_fallback(self):
        with patch.object(session, 'hypr_json', return_value=[self.monitor()]), \
                patch.object(session, 'query', side_effect=['false', 'Invalid dispatcher', 'ok']) as query:
            session.restore_pointer(('DP-1', .25, .25))
        self.assertEqual(query.call_args.args, ('hyprctl', 'dispatch', 'movecursor', '1060', '2520'))

    def test_waits_for_all_async_windows_and_late_close_events(self):
        states = [set(), {'one', 'two'}, {'two'}, set(), {'two'}, set(), set()]
        child = Mock()
        child.wait.return_value = 0
        with patch.object(session, 'screensaver_windows', side_effect=states) as windows, \
                patch.object(session, 'capture_pointer', return_value=('DP-1', .25, .25)), \
                patch.object(session.subprocess, 'Popen', return_value=child), \
                patch.object(session.time, 'sleep'), \
                patch.object(session, 'restore_pointer') as restore:
            self.assertEqual(session.run(['fake-launcher']), 0)
            self.assertEqual(windows.call_count, 7)
            restore.assert_called_once_with(('DP-1', .25, .25))

    def test_failed_launch_preserves_status_and_restores_pointer(self):
        child = Mock()
        child.wait.return_value = 7
        with patch.object(session, 'screensaver_windows', return_value=set()), \
                patch.object(session, 'capture_pointer', return_value=('DP-1', .25, .25)), \
                patch.object(session.subprocess, 'Popen', return_value=child), \
                patch.object(session.time, 'sleep'), \
                patch.object(session, 'restore_pointer') as restore:
            self.assertEqual(session.run(['fake-launcher']), 7)
            restore.assert_called_once()

    def test_existing_screensaver_is_not_restored_by_second_invocation(self):
        child = Mock()
        child.wait.return_value = 0
        with patch.object(session, 'screensaver_windows', return_value={'existing'}), \
                patch.object(session, 'capture_pointer') as capture, \
                patch.object(session.subprocess, 'Popen', return_value=child), \
                patch.object(session, 'restore_pointer') as restore:
            session.run(['fake-launcher'])
            capture.assert_not_called()
            restore.assert_not_called()

    def test_unavailable_compositor_does_not_prevent_launch(self):
        with patch.object(session, 'hypr_json', return_value=None):
            self.assertEqual(session.run(['/bin/true']), 0)
        with patch.object(session.subprocess, 'run', side_effect=subprocess.TimeoutExpired('hyprctl', 3)):
            self.assertIsNone(session.hypr_json('cursorpos'))


if __name__ == '__main__':
    unittest.main()
