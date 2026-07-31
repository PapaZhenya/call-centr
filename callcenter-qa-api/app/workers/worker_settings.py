from arq import func
from arq.connections import RedisSettings

from app.config import settings
from app.workers.tasks import evaluate_call_qa, ping, transcribe_call


class WorkerSettings:
    functions = [
        func(ping, max_tries=1),
        func(transcribe_call, max_tries=3),
        func(evaluate_call_qa, max_tries=3),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
