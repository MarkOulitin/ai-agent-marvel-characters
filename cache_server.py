from dotenv import load_dotenv
from logger import logger
import redis
import os

load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

logger.info(f'Connecting to redis database at {redis_host}:{redis_port}')
try:
    pool = redis.ConnectionPool(
        host=redis_host,
        port=redis_port,
        db=0,
        decode_responses=True
    )

    redis_client = redis.Redis(connection_pool=pool)

    redis_client.ping()
except Exception as e:
    logger.error(f'Error on connecting to redis: {e}')
    logger.exception(e)
    exit(1)
logger.info(f'Connected to redis')

def set_key_value(key, value, request_id=None):
    """Set a key-value pair in Redis"""
    try:
        redis_client.set(key, value)
        logger.info(f"Successfully added key in redis cache, request_id {request_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting key '{key}': {e}, request_id {request_id}")
        return False

def get_value(key, request_id=None):
    """Get value for a key from Redis"""
    try:
        value = redis_client.get(key)
        return value
    except Exception as e:
        logger.error(f"Error getting value for key '{key}': {e}, request_id {request_id}")
        return None
    
if __name__ == '__main__':
    set_key_value("how are you doing?", "good")
    logger.info('get_value: ', get_value('how are you doing?'))
    logger.info('get_value: ', get_value('how?'))
    