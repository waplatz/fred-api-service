from fastapi import FastAPI, HTTPException, Header, Depends, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import requests
import os
import csv
import io

# 🔹 Load environment variables
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")
print("DEBUG: Loaded FRED_API_KEY =", FRED_API_KEY)

# 🔹 Basic MVP developer API key (for direct API usage)
API_KEY = "my-secret-mvp-key"

# 🔹 Initialize FastAPI and Jinja2 templates
app = FastAPI(title="FRED Data API with Public UI")
templates = Jinja2Templates(directory="templates")

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# ✅ Authentication for developer API endpoints
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

# ✅ Fetch FRED data
def fetch_fred_series(series_id: str, start_date=None, end_date=None):
    params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json"}
    if start_date:
        params["observation_start"] = start_date
    if end_date:
        params["observation_end"] = end_date

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()

# ✅ Convert JSON observations to CSV
def observations_to_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "value"])
    for obs in data["observations"]:
        writer.writerow([obs["date"], obs["value"]])
    return output.getvalue()

# ✅ Public UI Home
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ✅ Public UI Download (No API Key Required)
@app.get("/download")
def download_data(dataset: str, start_date: str = None, end_date: str = None, format: str = "json"):
    series_map = {
        "gdp": "GDP",
        "inflation": "CPIAUCSL",
        "interest-rates": "FEDFUNDS",
        "unemployment": "UNRATE",
        "housing-starts": "HOUST"
    }

    series_id = series_map.get(dataset)
    if not series_id:
        raise HTTPException(status_code=400, detail="Invalid dataset")

    data = fetch_fred_series(series_id, start_date, end_date)

    if format == "csv":
        csv_data = observations_to_csv(data)
        return Response(content=csv_data, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={dataset}.csv"})

    return data

# ✅ Developer API Endpoints (Require API Key)
def create_endpoints(name, series_id):
    @app.get(f"/{name}")
    def get_series(start_date: str = None, end_date: str = None, auth: str = Depends(verify_api_key)):
        return fetch_fred_series(series_id, start_date, end_date)

    @app.get(f"/{name}/csv")
    def get_series_csv(start_date: str = None, end_date: str = None, auth: str = Depends(verify_api_key)):
        data = fetch_fred_series(series_id, start_date, end_date)
        csv_data = observations_to_csv(data)
        return Response(content=csv_data, media_type="text/csv")

# ✅ Create protected developer endpoints
create_endpoints("gdp", "GDP")
create_endpoints("inflation", "CPIAUCSL")
create_endpoints("interest-rates", "FEDFUNDS")
create_endpoints("unemployment", "UNRATE")
create_endpoints("housing-starts", "HOUST")

