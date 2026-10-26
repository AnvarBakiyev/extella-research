import time
from redis import Redis
from rq import Queue
plan = "a = 10\nb = 3\nanswer = a / b"; prob = "Tom has $10 and splits it among 3 friends. How much does each get?"
for qn in ("mac", "server"):
    job = Queue(qn, connection=Redis()).enqueue("jobs.run_plan_job", plan, prob, "plan")
    while job.get_status() not in ("finished", "failed"): time.sleep(0.2)
    r = job.return_value(); print(qn, r.get("answer"), r.get("host"))
