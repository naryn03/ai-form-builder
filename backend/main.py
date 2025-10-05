# main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict
from sqlalchemy.orm import Session
from db import init_db, SessionLocal
from models import Form, Submission
from langgraph_workflow import build_form_workflow

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(title="Dynamic Form Builder (LangGraph)")

@app.on_event("startup")
def on_start():
    init_db()
    # Build and compile graph once at startup
    app.state.graph = build_form_workflow()


# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------- Request Models -------------------

class CreateFormReq(BaseModel):
    description: str


class ValidateReq(BaseModel):
    form_id: int
    submission: Dict[str, Any]


class RecoverReq(BaseModel):
    form_id: int
    submission: Dict[str, Any]


# ------------------- Routes -------------------

@app.post("/create_form")
def create_form(req: CreateFormReq, db: Session = Depends(get_db)):
    graph = app.state.graph

    # Instead of accessing node handlers manually, invoke the graph
    result = graph.invoke({"mode": "schema", "description": req.description})
    print(result)
    schema = result.get("schema")
    if not schema:
        raise HTTPException(status_code=500, detail="Schema generation failed")

    form = Form(title=schema.get("title", "Untitled"), schema=schema)
    db.add(form)
    db.commit()
    db.refresh(form)
    return {"form_id": form.id, "schema": form.schema}


@app.post("/validate_submission")
def validate_submission(req: ValidateReq, db: Session = Depends(get_db)):
    form = db.get(Form, req.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    print("Form Schema:", form.schema)
    graph = app.state.graph
    result = graph.invoke({
        "mode": "validate",
        "schema": form.schema,
        "submission": req.submission
    })

    sub = Submission(
        form_id=form.id,
        data=req.submission,
        valid=result.get("validation_result", {}).get("valid", False),
        errors=result.get("validation_result", {}).get("errors", {})
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return {
        "submission_id": sub.id,
        "valid": sub.valid,
        "errors": sub.errors
    }


@app.post("/recover")
def recover(req: RecoverReq, db: Session = Depends(get_db)):
    form = db.get(Form, req.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    graph = app.state.graph
    result = graph.invoke({
        "mode": "recovery",
        "schema": form.schema,
        "submission": req.submission,
        "validation_result": {"errors": {}}  # could come from last submission
    })

    recovery = result.get("recovery", {})

    sub = Submission(
        form_id=form.id,
        data=req.submission,
        valid=False,
        errors=recovery.get("errors", {})
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return {
        "suggestions": recovery.get("suggestions", {}),
        "submission_id": sub.id
    }


@app.get("/analytics/{form_id}")
def analytics(form_id: int, db: Session = Depends(get_db)):
    form = db.get(Form, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    subs = db.query(Submission).filter(Submission.form_id == form_id).all()
    history = [s.data for s in subs]

    graph = app.state.graph
    result = graph.invoke({
        "mode": "learning",
        "schema": form.schema,
        "history": history
    })

    return {
        "insights": result.get("insights", {}),
        "total_submissions": len(history)
    }

@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")