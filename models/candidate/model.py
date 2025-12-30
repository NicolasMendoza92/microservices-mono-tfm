from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)

    experience = Column(JSON)  # lista de { title, company, years }
    skills = Column(JSON)

    # 🔽 muchas otras columnas que NO usaremos
    raw_cv = Column(String)
    created_at = Column(String)
