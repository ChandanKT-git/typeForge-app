from slowapi import Limiter
from slowapi.util import get_remote_address
import os

limiter = Limiter(key_func=get_remote_address, enabled=os.environ.get("TESTING", "0") != "1")
