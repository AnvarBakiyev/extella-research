"""Вызов на сервере: поставить план в очередь mac и дождаться ответа."""
import sys, time
from redis import Redis
from rq import Queue
q = Queue(sys.argv[1] if len(sys.argv) > 1 else "mac", connection=Redis())
plan = "eggs [eggs] = 16\neaten [eggs] = 3 + 4\nsold [eggs] = eggs - eaten\nanswer [dollars] = sold * 2"
problem = "Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?"
t0 = time.time(); job = q.enqueue("jobs.run_plan_job", plan, problem, "plan")
while job.get_status() not in ("finished", "failed"): time.sleep(0.2)
print(job.get_status(), job.return_value(), round(time.time() - t0, 2), "s")
