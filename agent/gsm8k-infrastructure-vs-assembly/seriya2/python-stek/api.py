from fastapi import FastAPI
from pydantic import BaseModel
from solver import solve

app = FastAPI()

class Q(BaseModel):
    question: str

@app.post("/solve")
def solve_http(q: Q):
    return solve(q.question)
