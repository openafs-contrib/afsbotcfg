"""
Fake Gerrit server for Buildbot master testing.
"""

# pylint: disable=broad-exception-caught

import argparse
import datetime
import http.server
import json
import logging
import os
import queue
import socket
import socketserver
import sys
import threading
import time
import typing
import urllib.parse

try:
    import paramiko
except ImportError:
    print("Error: The paramiko module is required.")
    sys.exit(1)

DEFAULT_HTTP_PORT = 8000
DEFAULT_SSH_PORT = 29418

log = logging.getLogger(__name__)


def generate_event(branch, counter):
    """Generate a fake gerrit event to trigger builds."""
    event = {
        "type": "patchset-created",
        "uploader": {
            "name": "John Doe",
            "email": "jdoe@example.com",
            "username": "jdoe",
        },
        "patchSet": {
            "number": f"{counter}",
            "revision": f"{counter:040}",
            "parents": ["a4ee6a4d185599f6de05eedc70ff737f1a6d1851"],
            "ref": f"refs/changes/44/12744/{counter}",
            "uploader": {
                "name": "John Doe",
                "email": "jdoe@example.com",
                "username": "jdoe",
            },
            "createdOn": 1761307878,
            "author": {
                "name": "John Doe",
                "email": "jdoe@example.com",
                "username": "",
            },
            "isDraft": False,
            "kind": "TRIVIAL_REBASE",
            "sizeInsertions": 2,
            "sizeDeletions": -1,
        },
        "change": {
            "project": "openafs",
            "branch": f"{branch}",
            "topic": "buildbot-check",
            "id": "Ib953a9eec8a0e9234aee5e959643f7cfdee87410",
            "number": "12744",
            "subject": "Do not submit: Check buildbot verification",
            "owner": {
                "name": "John Doe",
                "email": "jdoe@example.com",
                "username": "jdoe",
            },
            "url": "http://localhost:8000/12744",
            "commitMessage": """\
Check buildbot verification

A test change to check buildbot and gerrit integration.

Change-Id: Ib953a9eec8a0e9234aee5e959643f7cfdee87410
""",
            "status": "NEW",
        },
        "project": "openafs",
        "refName": f"refs/heads/{branch}",
        "changeKey": {"id": "Ib953a9eec8a0e9234aee5e959643f7cfdee87410"},
        "eventCreatedOn": 1761307880,
    }
    return json.dumps(event) + "\n"


class FakeGerritState:
    """Manages shared state between the HTTP server and the Paramiko SSH server."""

    def __init__(self):
        # Stores build results received from GerritStatusPush via 'gerrit review' command
        # Key: timestamp -> Value: Full command string sent by Buildbot
        self.results: typing.Dict[str, str] = {}
        # Queue for change events to be sent via the SSH Event Streamer
        self.event_queue = queue.Queue()
        # Counter for generating unique fake change IDs
        self.change_id_counter = 1
        # Lock for thread-safe access to shared state
        self.lock = threading.Lock()
        log.info("Fake Gerrit State Initialized.")

    def enqueue_change(self, branch):
        """Generates a new fake change event and puts it in the queue."""
        with self.lock:
            change_id = str(self.change_id_counter)
            event = generate_event(branch, self.change_id_counter)
            self.change_id_counter += 1
            self.event_queue.put(event)
            return f"Change {change_id} enqueued successfully."

    def add_result(self, command: str):
        """Stores a received build result command from 'gerrit review'."""
        command = command.strip()
        key = str(time.time())
        with self.lock:
            self.results[key] = command
        log.info("Received status push result: %s", command)


class GerritSSHSession(paramiko.ServerInterface):
    """Handles the SSH session logic for Gerrit commands."""

    def __init__(self, state: FakeGerritState, username: str):
        self.state = state
        self.username = username
        self.event = threading.Event()

    # Authentication Methods
    def check_auth_password(self, username, password):
        # Allow any password for testing
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # Allow any public key for testing
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        # Allow password and public key auth
        return "password,publickey"

    # Channel Request Handling
    def check_channel_request(self, kind, chanid):
        # Only allow 'session' channels for command execution
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        command = command.decode("utf-8").strip()
        log.info("SSH command received: >>>%s<<<", command)

        if command == "gerrit version":
            channel.sendall(b"gerrit version 2.13.13\n")
            channel.send_exit_status(0)  # buildbot checks the exit code
            channel.close()
            result = True
        elif command == "gerrit stream-events":
            threading.Thread(target=self._stream_events, args=(channel,)).start()
            result = True
        elif command.startswith("gerrit review"):
            self._handle_gerrit_review(channel, command)
            result = True
        else:
            channel.sendall(f"ERROR: Unknown command '{command}'\n".encode("utf-8"))
            channel.close()
            result = False
        return result

    def _stream_events(self, channel: paramiko.Channel):
        """Sends queued change events over the channel (for GerritChangeSource)."""
        client_address = channel.getpeername()
        log.info("SSH Stream Events started for %s", client_address)
        try:
            # Send events from the queue indefinitely
            while not self.event.is_set():
                # Get event string from the queue, wait up to 1 second
                try:
                    event_string = self.state.event_queue.get(timeout=1)
                    log.info("SSH Streamer: Sending event...")
                    channel.sendall(event_string.encode("utf-8"))
                    self.state.event_queue.task_done()
                    # Wait a moment before checking the queue again
                    time.sleep(0.1)
                except queue.Empty:
                    # Keep the connection alive while waiting for new events
                    pass
        except Exception as e:
            log.error("SSH Streamer Error: %s", e)
        finally:
            log.info("SSH Stream Events closed for %s", client_address)
            channel.close()

    def _handle_gerrit_review(self, channel: paramiko.Channel, command: str):
        """Handles the build status push (for GerritStatusPush)."""
        # Command format: gerrit review <change>,<patchset> --label=... --message='...'

        # Store the entire command line as the result
        self.state.add_result(command)

        # Send a success message and close the channel immediately
        channel.sendall(b"gerrit review command executed (Simulated OK)\n")
        channel.send_exit_status(0)  # buildbot checks the exit code
        channel.close()


def ssh_session_handler(
    client_socket: socket.socket, host_key: paramiko.RSAKey, state: FakeGerritState
):
    """Handles a single SSH connection using Paramiko."""
    try:
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)

        # Use a dummy username for the session interface
        server = GerritSSHSession(state, username="buildbot")

        transport.start_server(server=server)

        # Wait until the transport is closed (either naturally or by error)
        while transport.is_active():
            time.sleep(0.5)
    except Exception as e:
        log.error("SSH Transport Error: %s", e)
    finally:
        if "transport" in locals() and transport.is_active():
            transport.close()
        client_socket.close()
        log.info("SSH Connection closed.")


class GerritControlServer(socketserver.TCPServer):
    """Custom TCPServer to hold and pass the shared state to the handler."""

    def __init__(self, server_address, RequestHandlerClass, state: FakeGerritState):
        self.state = state
        super().__init__(server_address, RequestHandlerClass)


class GerritControlHandler(http.server.BaseHTTPRequestHandler):
    """Handles requests for triggering events and viewing results."""

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        log.info("[%s] %s", self.address_string(), format % args)

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def _parse_post_data(self):
        """Parses application/x-www-form-urlencoded data."""
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")
        return urllib.parse.parse_qs(post_data)

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET method requests."""
        if self.path.startswith("/"):
            # Parse query parameters for status messages
            path_parts = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(path_parts.query)

            # Extract status message for display
            status_message = query.get("message", [""])[0]
            status_type = query.get("status", [""])[0]

            # Server-Side rendering of results
            keys = sorted(self.server.state.results.keys(), key=float, reverse=True)
            output = ""

            if keys:
                for key in keys:
                    # Format timestamp for display
                    date = datetime.datetime.fromtimestamp(float(key)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    content = self.server.state.results[key]
                    output += f"--- Timestamp: {date} ---\n{content}\n\n"
            else:
                output = "No build results received yet."

            result_count = len(keys)
            # End rendering

            self._set_headers(content_type="text/html")
            # Pass all dynamic content to the HTML generation function
            html_content = self.get_homepage_html(
                status_type, status_message, output.strip(), result_count
            )
            self.wfile.write(html_content.encode("utf-8"))
            log.info("HTTP GET / served")
        else:
            self._set_headers(404, content_type="text/plain")
            self.wfile.write(b"404 Not Found")

    def do_POST(self):  # pylint: disable=invalid-name
        """Handle POST method requests."""
        if self.path == "/trigger_change":
            form_data = self._parse_post_data()
            # Extract the branch_name field from the form data
            branch = form_data.get("branch_name", ["master"])[0]
            try:
                # Enqueue the change event
                message = self.server.state.enqueue_change(branch)

                # Post/Redirect/Get Pattern: Redirect back to home with status message
                self.send_response(303)
                status = "success"
                message = urllib.parse.quote(message)
                branch = urllib.parse.quote(branch)
                url = f"/?status={status}&message={message}&branch={branch}"
                self.send_header("Location", url)
                self.end_headers()
                log.info("HTTP POST /trigger_change success.")
            except Exception as e:
                error_msg = f"Failed to enqueue change: {e}"
                self.send_response(303)
                status = "error"
                message = urllib.parse.quote(error_msg)
                url = f"/?status={status}&message={message}"
                self.send_header("Location", url)
                self.end_headers()
                log.info("HTTP POST /trigger_change error.")
        else:
            self._set_headers(404, content_type="text/plain")
            self.wfile.write(b"404 Not Found")

    def get_homepage_html(
        self,
        status_type: str,
        status_message: str,
        results_content: str,
        results_count: int,
    ):
        """Generates a simple HTML interface using only standard forms and server-side rendering."""

        # Determine the status display based on server action
        status_html = ""
        if status_message:
            status_class = "success" if status_type == "success" else "error"
            status_text = "SUCCESS" if status_type == "success" else "ERROR"
            status_html = f"""
            <p id="triggerStatus" class="text-sm" style="margin-top: 10px;">
                <span class="{status_class} text-bold">{status_text}:</span> {status_message}
                <br> <span>Queue size: {self.server.state.event_queue.qsize()}</span>
            </p>
            """
        css = """
        /* Minimal CSS for readability and structure */
        body { font-family: sans-serif; margin: 0; padding: 20px; background-color: #f3f4f6; }
        .container { max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        h1 { font-size: 24px; font-weight: bold; color: #111827; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid #e5e7eb; }
        h2 { font-size: 20px; font-weight: 600; margin-bottom: 10px; }
        .section-blue { margin-bottom: 20px; padding: 15px; background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; }
        .section-green { margin-bottom: 20px; padding: 15px; background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; }
        .button { display: inline-block; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: background-color 0.3s; border: none; }
        .button-blue { background-color: #2563eb; color: white; }
        .button-blue:hover { background-color: #1d4ed8; }
        .button-green { background-color: #059669; color: white; }
        .button-green:hover { background-color: #047857; }
        .console { height: 300px; overflow-y: scroll; background: #1f2937; color: #f9fafb; padding: 1rem; border-radius: 0.5rem; white-space: pre-wrap; font-family: monospace; font-size: 12px; margin-top: 10px; }
        .text-sm { font-size: 14px; color: #6b7280; }
        .text-xs { font-size: 12px; color: #4b5563; }
        .text-bold { font-weight: bold; }
        .success { color: #10b981; }
        .error { color: #ef4444; }
        input[type="text"] { width: 100%; padding: 8px; border: 1px solid #bfdbfe; border-radius: 4px; box-sizing: border-box; font-size: 14px; }
"""

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fake Gerrit Control</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fake Gerrit Server</h1>
        <p class="text-sm" style="margin-bottom: 20px;">
            Simulate gerrit for buildbot master testing.
        </p>

        <!-- Status Message Display -->
        {status_html}

        <!-- Trigger Change Section -->
        <div class="section-blue">
            <h2 style="color: #1e3a8a;">Trigger New Change Event</h2>

            <form method="POST" action="/trigger_change">
                <div style="margin-bottom: 15px;">
                    <label for="branchName" class="text-sm text-bold" style="display: block; margin-bottom: 5px;">Target Branch:</label>
                    <!-- Use name="branch_name" for form submission handling -->
                    <input type="text" id="branchName" name="branch_name" value="master">
                    <p class="text-xs" style="margin-top: 5px;">Enter the branch (e.g., 'master', 'release-1.0') for the change event.</p>
                </div>

                <button type="submit" class="button button-blue">
                    Generate Fake Change
                </button>
            </form>
        </div>

        <!-- Build Results Section -->
        <div class="section-green">
            <h2 style="color: #065f46;">Build Results</h2>
            <p class="text-xs" style="margin-bottom: 10px;">Shows the full command line sent by Buildbot's GerritStatusPush (e.g., <span class="text-bold">'gerrit review 1000,1 --label=Verified=1'</span>).</p>

            <!-- Refresh Button  -->
            <form method="GET" action="/" style="display: inline;">
                <button type="submit" class="button button-green" style="margin-right: 10px;">
                    Refresh Results
                </button>
            </form>

            <span id="resultsCount" style="font-size: 16px; font-weight: 600; color: #065f46;">
              Total Results: {results_count}
            </span>
            <pre id="resultsConsole" class="console">{results_content}</pre>
        </div>

    </div>
</body>
</html>
"""


def start_http_server(port: int, state: FakeGerritState):
    """Starts the HTTP control server in a dedicated thread."""
    httpd = GerritControlServer(("", port), GerritControlHandler, state)
    log.info("HTTP server running on http://localhost:%d", port)
    httpd.serve_forever()


def format_known_hosts_line(key: paramiko.RSAKey, port: int) -> str:
    """Formats the RSA key into a known_hosts file line."""
    hostname = "localhost"  # Running in a podman pod
    key_type = key.get_name()
    key_base64 = str(key.get_base64())
    return f"[{hostname}]:{port} {key_type} {key_base64}"


def write_known_hosts_file(keydir: str, host_key: paramiko.RSAKey, port: int) -> None:
    """Save the host key to a file in the known_hosts format."""
    known_hosts_file_path = f"{keydir}/fake_gerrit_known_hosts"
    try:
        with open(known_hosts_file_path, "w", encoding="ascii") as f:
            line = format_known_hosts_line(host_key, port)
            f.write(f"{line}\n")
        log.info("Wrote public ssh host key to %s", known_hosts_file_path)
    except Exception as e:
        logging.error("Could not save known_hosts to %s: %s", known_hosts_file_path, e)


def create_host_key(keydir: str) -> paramiko.RSAKey:
    """Read the SSH host key from a file. If unable to read the key,
    generate a new one and write it to the key file."""
    key_file_path = f"{keydir}/fake_gerrit_rsa_key"
    host_key = None
    try:
        host_key = paramiko.RSAKey.from_private_key_file(key_file_path)
        logging.info("Loaded host key from %s", key_file_path)
    except FileNotFoundError:
        logging.warning("Host key file not found at %s", key_file_path)
    except paramiko.SSHException as e:
        logging.error("Error loading host key: %s", e)
    except Exception as e:
        logging.error("An unexpected error occurred during key loading: %s", e)

    if host_key is None:
        logging.info("Generating a new 2048-bit RSA host key.")
        host_key = paramiko.RSAKey.generate(2048)
        try:
            host_key.write_private_key_file(key_file_path)
            logging.info("Host key written to %s", key_file_path)
        except Exception as e:
            # The server will still use the generated key this session, but it won't persist.
            logging.error("Could not save host key to %s: %s", key_file_path, e)

    return host_key


def start_gerrit_server(keydir: str, port: int, state: FakeGerritState):
    """Starts the SSH server on the Gerrit port."""

    try:
        host_key = create_host_key(keydir)
        write_known_hosts_file(keydir, host_key, port)
    except Exception as e:
        log.error("Failed to generate RSA key: %s", e)
        return

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("", port))
        server_socket.listen(5)
        log.info("SSH Server running on port %d", port)
    except Exception as e:
        log.error("Failed to bind SSH server on port %d: %s", port, e)
        return

    while True:
        try:
            client_socket, addr = server_socket.accept()
            log.info("New SSH connection from %s", addr)

            # Start the SSH transport handshake in a new thread
            targs = (client_socket, host_key, state)
            t = threading.Thread(target=ssh_session_handler, args=targs)
            t.daemon = True
            t.start()
        except KeyboardInterrupt:
            server_socket.close()
            break
        except Exception as e:
            log.error("Server accept error: %s", e)


def main():
    """Process command line arguments and start the server."""
    parser = argparse.ArgumentParser(
        prog="fake_gerrit",
        description="Simulate gerrit code review for Buildbot testing.",
    )
    parser.add_argument(
        "--http-port",
        metavar="<port>",
        type=int,
        help="http port [%(default)s]",
        default=DEFAULT_HTTP_PORT,
    )
    parser.add_argument(
        "--ssh-port",
        metavar="<port>",
        type=int,
        help="ssh port [%(default)s]",
        default=DEFAULT_SSH_PORT,
    )
    parser.add_argument(
        "--logdir",
        metavar="<path>",
        help="Log file directory [%(default)s]",
        default=os.getcwd(),
    )
    parser.add_argument(
        "--keydir",
        metavar="<path>",
        help="SSH host key file directory [%(default)s]",
        default=os.getcwd(),
    )
    args = parser.parse_args()

    # Logging setup.
    logging.basicConfig(
        filename=f"{args.logdir}/fake_gerrit.log",
        encoding="utf-8",
        level=logging.DEBUG,
        format="%(asctime)s %(message)s",
    )
    log.info("Starting")

    # Initialize the shared state instance locally
    state = FakeGerritState()

    # Start the HTTP server in a separate thread
    http_args = (args.http_port, state)
    http_thread = threading.Thread(
        target=start_http_server, args=http_args, daemon=True
    )
    http_thread.start()

    # Start the Paramiko SSH server in the main thread (blocking call)
    try:
        start_gerrit_server(args.keydir, args.ssh_port, state)
    except KeyboardInterrupt:
        log.info("Shutting down servers...")


if __name__ == "__main__":
    main()
