from fastapi import FastAPI
from api import endpoints
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Financial Analysis API")

# CORS Middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows the React app origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(endpoints.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Financial Analysis API"}