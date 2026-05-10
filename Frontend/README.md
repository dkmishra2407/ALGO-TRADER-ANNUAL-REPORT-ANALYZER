# Frontend (React + Vite)

This is a React frontend for the FastAPI backend.

## Features

- Check API health (`GET /`)
- Load available strategies (`GET /strategies`)
- Run backtests (`POST /run_backtest`)
- Create persistent custom strategies (`POST /custom_strategy`)
- Run one-off custom strategy backtests (`POST /run_custom_backtest`)

## Run

1. Start backend:

```bash
cd Backend
python -m uvicorn main:app --reload
```

2. Install frontend dependencies:

```bash
cd Frontend
npm install
```

3. Start frontend:

```bash
npm run dev
```

4. Open the URL shown by Vite (usually `http://localhost:5173`).

## Notes

- Default API base URL in UI: `http://127.0.0.1:8000`
- Update the API URL in the form if your backend runs on another host/port.
