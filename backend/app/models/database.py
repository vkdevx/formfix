from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Configure SQLite or PostgreSQL
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables on application startup."""
    from app.models.user import User, SessionModel, Consent, OTPRecord, AuditLog
    from app.models.document import UploadedDocument
    from app.models.rules import FormTemplate, RuleSet, Rule
    Base.metadata.create_all(bind=engine)
