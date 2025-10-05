# How to start?

#### Copy .env.example to .env and fill in the values:
```bash
cp .env.example .env
```

#### Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
or Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### Run the application:
```bash
uvicorn main:app --reload --port PORT_NUMBER
```

### Test API endpoints:

#### Create a form:
Endpoint: POST /create_form

```json
{
    "description": "Create a job application form with name, email, phone, start date, end date if they're still employed, and years of experience"
}
```

#### Validate a submission:
Endpoint: POST /validate_submission

```json
{
    "form_id": 4,
    "submission": {
        "name": "Ashish Narayan",
        "email": "abc123@example.com",
        "phone": "+91-98765432100",
        "start_date": "2025-11-01",
        "end_date": "2026-12-31",
        "years_experience": 1
    }
}
```

#### Recover a submission:
Endpoint: POST /recover

```json
{
    "form_id": 4,
    "submission": {
        "name": "Ashish Narayan",
        "email": "abc123@example.com",
        "phone": "+91-98765432100",
        "start_date": "2025-11-01",
        "end_date": "2026-13-31",
        "years_experience": 1
    }
}
```
