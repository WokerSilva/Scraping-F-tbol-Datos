from dataclasses import dataclass


@dataclass
class PostgresConnection:
    dsn: str
    connected: bool = False

    def connect(self) -> None:
        self.connected = True
