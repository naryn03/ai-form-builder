# models.py
from sqlalchemy import Column, Integer, String, Boolean, JSON
from db import Base

class Form(Base):
    __tablename__ = "forms"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    schema = Column(JSON, nullable=False)   # JSON column (native when supported)
    version = Column(Integer, default=1)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, nullable=False, index=True)
    data = Column(JSON, nullable=False)
    valid = Column(Boolean, default=False)
    errors = Column(JSON, nullable=True)