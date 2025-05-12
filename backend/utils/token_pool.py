import threading
import time
from typing import List, Optional
from backend.app.config import app_configuration

class TokenPool:
    """
    Token pool for managing API tokens.
    Allows round-robin token selection and supports banning tokens (on rate limit or auth errors).
    Uses a configurable cooldown for banned tokens.
    """

    def __init__(self, tokens: List[str]):
        """
        Initialize the TokenPool with a list of tokens.
        """
        self.tokens = tokens
        self.lock = threading.Lock()
        self.index = 0
        self.banned = {}
        self.cooldown = getattr(app_configuration, "TOKEN_BAN_COOLDOWN", 600)

    def get_token(self) -> Optional[str]:
        """
        Get the next token in a round-robin model.
        Returns None if no tokens are available.
        """
        with self.lock:
            now = time.time()
            available = [t for t in self.tokens if t not in self.banned or self.banned[t] < now]
            if not available:
                return None
            token = available[self.index % len(available)]
            self.index = (self.index + 1) % len(available)
            return token

    def ban_token(self, token: str, cooldown: Optional[int] = None):
        """
        Remove a token from the pool (e.g. if it is rate-limited or invalid).
        """
        with self.lock:
            if token in self.tokens:
                until = time.time() + (cooldown or self.cooldown)
                self.banned[token] = until