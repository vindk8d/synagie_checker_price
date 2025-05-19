# HTML to Natural Language Converter

This application converts HTML content from CSV files into natural language text. It consists of a React frontend and a FastAPI backend.

## Project Structure

```
.
├── backend/
│   └── main.py
├── frontend/
│   ├── src/
│   │   └── App.js
│   ├── package.json
│   └── tailwind.config.js
└── requirements.txt
```

## Setup Instructions

### Backend Setup

1. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
cd backend
uvicorn main:app --reload
```

The backend will run on http://localhost:8000

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run the development server:
```bash
npm start
```

The frontend will run on http://localhost:3000

## Usage

1. Prepare a CSV file with HTML content in the first column
2. Open the application in your browser
3. Upload the CSV file using the file input
4. Click "Process File" to convert the HTML to natural language
5. The processed CSV file will be automatically downloaded

## API Endpoints

- POST `/process-csv`: Accepts a CSV file and returns a processed CSV with HTML and natural language columns

## Technologies Used

- Frontend: React, Tailwind CSS
- Backend: FastAPI
- HTML Processing: BeautifulSoup4
- Data Processing: Pandas 