"""Задание RQ: исполнить план текущей установленной версией исполнителя (~/pystek/current/steps_handler.py)."""
import importlib.util, os

def run_plan_job(plan, problem="", mode="plan"):
    path = os.path.expanduser("~/pystek/current/steps_handler.py")
    spec = importlib.util.spec_from_file_location("steps_live", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    out = m.run_plan(plan, problem, mode)
    out["host"] = os.uname().nodename
    return out
