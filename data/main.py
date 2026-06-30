from fastapi import FastAPI, Query
from database import fetch_all

app = FastAPI(
    title="Internal Data API",
    description="API interne pour exposer les données du datamart MariaDB",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API is running"}


@app.get("/defect")
def get_defects(limit: int = Query(100, ge=1, le=1000)):
    query = """
        SELECT *
        FROM defect
        LIMIT :limit
    """
    return fetch_all(query, {"limit": limit})


@app.get("/maps")
def get_maps(limit: int = Query(100, ge=1, le=1000)):
    query = """
        SELECT *
        FROM maps
        LIMIT :limit
    """
    return fetch_all(query, {"limit": limit})


@app.get("/die")
def get_die(limit: int = Query(100, ge=1, le=1000)):
    query = """
        SELECT *
        FROM die
        LIMIT :limit
    """
    return fetch_all(query, {"limit": limit})