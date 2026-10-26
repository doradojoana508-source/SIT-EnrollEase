import mysql.connector
from config import db_config


def get_connection():
    """Gumagawa ng bagong koneksyon sa MySQL gamit ang laman ng config.py."""
    return mysql.connector.connect(**db_config)