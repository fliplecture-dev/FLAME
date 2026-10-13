"""Windows background reload cannot rely on console Ctrl+C events."""
import sys
from pathlib import Path
import uvicorn
from uvicorn._subprocess import get_subprocess
from uvicorn.supervisors.watchfilesreload import WatchFilesReload

sys.path.insert(0, str(Path.cwd()))


class BackgroundReload(WatchFilesReload):
    def restart(self):
        # A detached Windows session has no interactive console to deliver
        # CTRL_C_EVENT to. Terminate only the owned worker, then reuse sockets.
        self.process.terminate()
        self.process.join(timeout=5)
        if self.process.is_alive():
            self.process.kill()
            self.process.join(timeout=5)
        if self.process.is_alive():
            raise RuntimeError('Previous API worker did not stop; refusing a duplicate.')
        self.process = get_subprocess(config=self.config, target=self.target, sockets=self.sockets)
        self.process.start()


if __name__ == '__main__':
    config = uvicorn.Config('app.main:app', host='127.0.0.1', port=8000,
                            reload=True, reload_dirs=['app'], access_log=False)
    server = uvicorn.Server(config)
    BackgroundReload(config, target=server.run, sockets=[config.bind_socket()]).run()
