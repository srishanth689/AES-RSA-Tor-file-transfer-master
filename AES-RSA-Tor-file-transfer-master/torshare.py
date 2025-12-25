import os
import shutil
import multiprocessing

from stem.control import Controller
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)


@app.route('/')
def index():
    return render_template("index.html", filename=app.config.get("FILE_NAME"), filesize=app.config.get("FILE_SIZE"))


@app.route('/download')
def download():
    return send_from_directory(app.config.get("FILE_DIR"), app.config.get("FILE_NAME"), as_attachment=True)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html")


def run_flask_app(filepath=None):
    """Top-level callable for multiprocessing on Windows.
    Running Flask via a top-level function avoids pickling issues when using
    the 'spawn' start method (default on Windows).

    If `filepath` is provided, set the app config values before starting the
    server so `/download` has a valid directory and filename.
    """
    if filepath:
        app.config["FILE_DIR"] = os.path.dirname(filepath)
        app.config["FILE_NAME"] = os.path.basename(filepath)
        try:
            app.config["FILE_SIZE"] = os.path.getsize(filepath)
        except Exception:
            app.config["FILE_SIZE"] = None

    # Bind to localhost:5000 so the hidden-service target_port matches.
    app.run(host='127.0.0.1', port=5000)


class TorShare:
    def __init__(self):
        self.controller = None  # type: Controller
        self.control_ports = [9051, 9151]
        self.hostname = None
        self.hidden_service_dir = None
        self.app_process = None

    def connect(self):
        for controlport in self.control_ports:
            try:
                self.controller = Controller.from_port(port=controlport)
            except Exception as e:
                print(e)

    def authenticate(self):
        self.controller.authenticate()

    def is_connected(self):
        return self.controller is not None

    def create_service(self, filepath):
        # If a service is already running, stop it first so the new file is served
        if self.app_process is not None and self.app_process.is_alive():
            try:
                self.stop_service()
            except Exception:
                # best-effort stop; continue to try starting a new service
                pass

        # Try to create an ephemeral (in-memory) hidden service first (uses ADD_ONION)
        # Ephemeral hidden services do not require Tor to write files and are more portable.
        self._set_file_config(filepath)
        # start the web app process so the target port is available
        # use a top-level function so the Process target is picklable on Windows
        # pass the filepath so the child process can set app.config values
        self.app_process = multiprocessing.Process(target=run_flask_app, name="app", args=(filepath,))
        self.app_process.start()

        try:
            # mapping: public port -> target port
            mapping = {80: 5000}
            result = self.controller.create_ephemeral_hidden_service(mapping, await_publication=True)
            # result may be an object with .service_id, or a tuple (service_id, private_key)
            service_id = None
            if hasattr(result, 'service_id'):
                service_id = result.service_id
            elif isinstance(result, (tuple, list)) and len(result) > 0:
                service_id = result[0]

            if service_id:
                # ephemeral service id doesn't include .onion
                self.hostname = service_id + '.onion'
                # remember ephemeral id so we can remove it later
                self.ephemeral_service_id = service_id
                return
        except Exception:
            # ephemeral creation failed (older Tor or permission issues) -> fall back
            pass

        # Fallback: file-based hidden service (original behavior)
        self.hidden_service_dir = os.path.join(self.controller.get_conf('DataDirectory', '/tmp'), 'torshare')
        result = self.controller.create_hidden_service(self.hidden_service_dir, 80, target_port=5000)
        self.hostname = result.hostname

    def stop_service(self):
        # Remove ephemeral hidden service if present
        try:
            if hasattr(self, 'ephemeral_service_id') and self.ephemeral_service_id:
                try:
                    # remove ephemeral hidden service (may raise if not supported)
                    self.controller.remove_ephemeral_hidden_service(self.ephemeral_service_id)
                except Exception:
                    pass
                self.ephemeral_service_id = None

            # Remove file-based hidden service if present
            if self.hidden_service_dir:
                try:
                    self.controller.remove_hidden_service(self.hidden_service_dir)
                except Exception:
                    pass
                try:
                    shutil.rmtree(self.hidden_service_dir)
                except Exception:
                    pass
                self.hidden_service_dir = None
        except Exception as e:
            # best-effort cleanup; log and continue
            print("Error while stopping hidden service:", e)

        # Terminate the Flask app process if running
        try:
            if self.app_process is not None:
                if self.app_process.is_alive():
                    self.app_process.terminate()
                    self.app_process.join(timeout=2)
                self.app_process = None
        except Exception:
            pass

        # clear hostname so callers know service stopped
        self.hostname = None

    def _set_file_config(self, filepath):
        app.config["FILE_DIR"] = os.path.dirname(filepath)
        app.config["FILE_NAME"] = os.path.basename(filepath)
        app.config["FILE_SIZE"] = os.path.getsize(filepath)


if __name__ == '__main__':
    app.run()
