import redis

r = redis.Redis(host="localhost", port=6379)
try:
    r.ping()
    print("Connected to Redis!")
except redis.ConnectionError:
    print("Could not connect to Redis")
