
# Wind Forecast Analysis

A application that evaluates UK wind-generation forecasts against actual generation data using the Elexon BMRS API. It helps users understand forecast accuracy using only the information available at the time of a purchasing decision.

**Live Application:** https://wind-forecast-analysis-dun.vercel.app  
**Backend API:** https://wind-forecast-analysis.onrender.com  
**GitHub Repository:** https://github.com/Safal2004/Wind-Forecast-Analysis

## Overview

Electricity buyers need to make purchasing decisions based on the forecasts available at that moment. This application selects eligible wind-generation forecasts published before a defined purchasing decision cutoff, compares them with actual generation for matching delivery periods, and calculates forecast-error metrics.

Users can configure:
- Forecast publication start and end timestamps
- Actual-generation settlement date
- Purchasing decision cutoff

The dashboard displays summary metrics, forecast-versus-actual charts, forecast errors, and a delivery-period results table.


## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Python, FastAPI, Uvicorn |
| Data Source | Elexon BMRS API |
| Testing | pytest |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |
| Containerization | Docker, Docker Compose |

## Features

- Fetches wind forecast and actual-generation data from the Elexon BMRS API.
- Selects the latest eligible forecast for each delivery period.
- Prevents forecasts published after the purchasing decision cutoff from being used.
- Matches forecast and actual records by delivery start time.
- Handles invalid values and ambiguous duplicate records.
- Calculates MAE, RMSE, and mean forecast bias.
- Displays interactive charts and delivery-period results.
- Provides a FastAPI backend and React frontend.
- Supports Docker-based local development and deployment.

## Data Sources

The application uses the following Elexon BMRS datasets:

- **WINDFOR:** Wind-generation forecast data.
- **FUELHH:** Half-hourly actual-generation data, filtered for wind.

Forecast records are retrieved using their publication-time range. Actual records are retrieved for the selected settlement date and filtered to avoid including records from adjacent settlement dates.

API documentation: https://bmrs.elexon.co.uk/

## Forecast Selection Methodology

For each delivery period, the application follows these steps:

1. Retrieve forecast records within the selected publication-time range.
2. Filter forecasts using the purchasing decision cutoff.
3. Select the latest eligible forecast for each delivery start time.
4. Match the selected forecast with actual generation using `startTime`.
5. Exclude invalid, missing, or ambiguous records that cannot be compared reliably.
6. Calculate forecast-error metrics using the remaining matched observations.


## Evaluation Metrics

Let:

- \(F_i\) = forecast generation for matched period \(i\)
- \(A_i\) = actual generation for matched period \(i\)
- \(n\) = number of matched periods

### Mean Absolute Error (MAE)

Measures the average absolute difference between forecast and actual generation.

\[
MAE = \frac{1}{n}\sum_{i=1}^{n}|F_i-A_i|
\]

### Root Mean Squared Error (RMSE)

Measures the square root of the average squared error. Larger errors have a greater effect on this metric.

\[
RMSE = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(F_i-A_i)^2}
\]

### Mean Forecast Bias

Measures the average signed difference between forecast and actual generation.

\[
Bias = \frac{1}{n}\sum_{i=1}^{n}(F_i-A_i)
\]

- Positive bias indicates over-forecasting.
- Negative bias indicates under-forecasting.
- Bias near zero indicates little average directional error, although individual errors may still be large.

The units of the metrics follow the units provided by the source data.

## Resolution and Data Limitations

WINDFOR forecast observations in the analysed data are hourly, while FUELHH actual-generation observations are half-hourly. Therefore, not every actual interval necessarily has a matching forecast observation.

The application reports the periods that can be matched under its timestamp-matching rules. It does not invent or interpolate additional forecast values.

For the example configuration of a 15 January 2026 settlement date and a 14 January 2026 decision cutoff, the dashboard displays 24 matched periods. Metrics describe those matched observations and should not be interpreted as covering every half-hour of the settlement day.

## Project Structure

```text
Wind-Forecast-Analysis/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── analysis.py
│   │   └── elexon_client.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .dockerignore
└── README.md
```

- `main.py` — FastAPI application and API routes.
- `analysis.py` — Forecast selection, matching, and metric calculations.
- `elexon_client.py` — Elexon API requests and data filtering.
- `tests/` — Backend test suite.
- `frontend/src/` — React dashboard and visualizations.

## Getting Started

### Prerequisites

- Git
- Python 3.12 or another version supported by the project
- Node.js and npm
- Docker Desktop and Docker Compose (for containerized setup)

### Option 1: Run with Docker Compose

Clone the repository:

```bash
git clone https://github.com/Safal2004/Wind-Forecast-Analysis.git
cd Wind-Forecast-Analysis
```

Build and start the application:

```bash
docker compose up --build
```

With the current local configuration, the services are available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

Stop the containers:

```bash
docker compose down
```

### Option 2: Run the Backend and Frontend Separately

#### Backend Setup

```bash
cd backend
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**Git Bash:**

```bash
source .venv/Scripts/activate
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install dependencies and start FastAPI:

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend runs at http://localhost:8000.

#### Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite displays the frontend URL in the terminal, commonly http://localhost:5173.

If running the frontend separately, configure the API base URL using the environment-variable name expected by the frontend code.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Checks backend availability |
| GET | `/api/periods` | Returns delivery-period results |
| GET | `/api/summary` | Returns summary metrics |
| GET | `/api/series` | Returns forecast and actual time-series data |

The analysis endpoints accept these query parameters:

- `publish_datetime_from` — Start of forecast publication-time range.
- `publish_datetime_to` — End of forecast publication-time range.
- `settlement_date_from` — Actual-generation settlement date.
- `purchasing_decision_cutoff` — Timestamp defining the purchasing decision cutoff.

Interactive API documentation:

https://wind-forecast-analysis.onrender.com/docs

## Testing

Run the backend tests:

```bash
cd backend
pytest
```

Build the frontend for production:

```bash
cd frontend
npm install
npm run build
```

Run these checks again after making changes to confirm that the application still works.

## Deployment

The application is deployed using separate frontend and backend services.

- **Frontend — Vercel:** https://wind-forecast-analysis-dun.vercel.app
- **Backend — Render:** https://wind-forecast-analysis.onrender.com

If the frontend uses the `VITE_API_BASE_URL` variable, configure it in Vercel as:

```text
VITE_API_BASE_URL=https://wind-forecast-analysis.onrender.com
```

Use the exact environment-variable name referenced in the frontend source code. If the variable changes, redeploy the frontend for the updated value to take effect.

The backend CORS configuration must allow the deployed frontend origin.

The current implementation can access the public Elexon API without a personal API key. Do not commit private credentials or `.env` files to the public repository.


