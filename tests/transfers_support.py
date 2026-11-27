from __future__ import annotations

import json
import socket
import ssl
import threading
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "transfers"
SCENARIOS = json.loads((FIXTURES / "smtp_scenarios.json").read_text(encoding="utf-8"))


class LocalSmtpServer:
    """Loopback SMTP server used only by integration tests."""

    def __init__(
        self,
        *,
        implicit_tls: bool = False,
        starttls: bool = True,
        data_code: int = 250,
        mail_code: int = 250,
        disconnect_after_data: bool = False,
    ) -> None:
        self.implicit_tls = implicit_tls
        self.starttls = starttls
        self.data_code = data_code
        self.mail_code = mail_code
        self.disconnect_after_data = disconnect_after_data
        self.commands: list[str] = []
        self.received_message = b""
        self.error: Exception | None = None
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self._listener.settimeout(0.2)
        self.port = self._listener.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        self._thread.join(timeout=3)

    def __enter__(self) -> LocalSmtpServer:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _serve(self) -> None:
        connection: socket.socket | ssl.SSLSocket | None = None
        reader = None
        try:
            while not self._stop.is_set():
                try:
                    connection, _address = self._listener.accept()
                    break
                except TimeoutError:
                    continue
                except OSError:
                    return
            if connection is None:
                return
            connection.settimeout(8)
            if self.implicit_tls:
                connection = self._wrap_tls(connection)
            reader = connection.makefile("rb")
            connection.sendall(b"220 localhost test SMTP ready\r\n")
            while True:
                line = reader.readline()
                if not line:
                    return
                command = line.decode("ascii", errors="replace").rstrip("\r\n")
                self.commands.append(command)
                upper = command.upper()
                if upper.startswith(("EHLO ", "HELO ")):
                    extensions = [b"250-localhost"]
                    if self.starttls and not self.implicit_tls and not isinstance(
                        connection,
                        ssl.SSLSocket,
                    ):
                        extensions.append(b"250-STARTTLS")
                    if isinstance(connection, ssl.SSLSocket):
                        extensions.append(b"250-AUTH PLAIN")
                    extensions.append(b"250 SIZE 50000000")
                    connection.sendall(b"\r\n".join(extensions) + b"\r\n")
                elif upper == "STARTTLS":
                    if not self.starttls:
                        connection.sendall(b"454 TLS not available\r\n")
                        continue
                    connection.sendall(b"220 Begin TLS\r\n")
                    reader.close()
                    connection = self._wrap_tls(connection)
                    reader = connection.makefile("rb")
                elif upper.startswith("MAIL FROM:"):
                    code = self.mail_code
                    response = b"test envelope response"
                    connection.sendall(f"{code} ".encode() + response + b"\r\n")
                elif upper.startswith("AUTH PLAIN "):
                    connection.sendall(b"235 test authentication accepted\r\n")
                elif upper.startswith("RCPT TO:"):
                    connection.sendall(b"250 recipient accepted\r\n")
                elif upper == "DATA":
                    connection.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    body_lines: list[bytes] = []
                    while True:
                        body_line = reader.readline()
                        if not body_line:
                            return
                        if body_line == b".\r\n":
                            break
                        body_lines.append(body_line)
                    self.received_message = b"".join(body_lines)
                    if self.disconnect_after_data:
                        return
                    connection.sendall(
                        f"{self.data_code} test final response\r\n".encode("ascii")
                    )
                elif upper == "QUIT":
                    connection.sendall(b"221 closing\r\n")
                    return
                else:
                    connection.sendall(b"250 ok\r\n")
        except (OSError, ssl.SSLError, TimeoutError) as error:
            self.error = error
        finally:
            if reader is not None:
                try:
                    reader.close()
                except OSError:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass

    def _wrap_tls(self, connection: socket.socket | ssl.SSLSocket) -> ssl.SSLSocket:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            FIXTURES / "localhost-test-cert.pem",
            FIXTURES / "localhost-test-key.pem",
        )
        return context.wrap_socket(connection, server_side=True)
