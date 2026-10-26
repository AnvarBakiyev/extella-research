"""Решатель GSM8K: логика v3.3 как есть, обёртка для потребителей."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import ustroystvo33 as C

def solve(question: str) -> dict:
    j = {"вызовов": 0, "токены": 0, "события": [], "согласие": None, "R": None, "P": None}
    answer = C.решить(question, j)
    return {"answer": answer, "agreement": bool(j["согласие"]), "model_calls": j["вызовов"]}
