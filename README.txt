To start:

cd backend
# First time only: copy .env.example to .env and adjust values for your machine.
python -m uvicorn app.main:app --reload --port 8000

cd frontend
npm run dev
