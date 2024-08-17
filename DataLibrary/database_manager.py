import os
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
'''
Author: Sean Baker
Date: 2024-07-21
Description: Database manager class to be implemented 
'''
# Ensure the DataLibrary folder exists
if not os.path.exists('DataLibrary'):
    os.makedirs('DataLibrary')

# SQLAlchemy setup
DATABASE_URL = "sqlite:///./DataLibrary/call_contexts.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CallContextModel(Base):
    __tablename__ = "call_contexts"

    call_sid = Column(String, primary_key=True, index=True)
    stream_sid = Column(String, index=True)
    call_ended = Column(Boolean, default=False)
    user_context = Column(Text)
    system_message = Column(String)
    initial_message = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    final_status = Column(String)
    to_number = Column(String, nullable=False)
    from_number = Column(String, nullable=False)

    def to_dict(self):
        return {
            "stream_sid": self.stream_sid,
            "call_sid": self.call_sid,
            "call_ended": self.call_ended,
            "user_context": json.loads(self.user_context),
            "system_message": self.system_message,
            "initial_message": self.initial_message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "final_status": self.final_status,
            "to_number": self.to_number,
            "from_number": self.from_number
        }

    def from_dict(self, data: dict):
        self.stream_sid = data.get("stream_sid", None)
        self.call_sid = data.get("call_sid", None)
        self.call_ended = data.get("call_ended", False)
        self.user_context = json.dumps(data.get("user_context", []))
        self.system_message = data.get("system_message", "")
        self.initial_message = data.get("initial_message", "")
        self.start_time = datetime.fromisoformat(data.get("start_time")) if data.get("start_time") else None
        self.end_time = datetime.fromisoformat(data.get("end_time")) if data.get("end_time") else None
        self.final_status = data.get("final_status", None)
        self.to_number = data.get("to_number", "")
        self.from_number = data.get("from_number", "")

# Create the database tables
Base.metadata.create_all(bind=engine)

class CallContext:
    def __init__(self, call_sid: str, stream_sid: str, call_ended: bool, user_context: List, system_message: str, initial_message: str, start_time: datetime, end_time: Optional[datetime], final_status: str, to_number: str, from_number: str):
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.call_ended = call_ended
        self.user_context = user_context
        self.system_message = system_message
        self.initial_message = initial_message
        self.start_time = start_time
        self.end_time = end_time
        self.final_status = final_status
        self.to_number = to_number
        self.from_number = from_number

class DatabaseManager:
    def __init__(self):
        self.SessionLocal = SessionLocal

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_call_context(self, db: Session, call_context: CallContext):
        db_call_context = CallContextModel(
            call_sid=call_context.call_sid,
            stream_sid=call_context.stream_sid,
            call_ended=call_context.call_ended,
            user_context=json.dumps(call_context.user_context),
            system_message=call_context.system_message,
            initial_message=call_context.initial_message,
            start_time=call_context.start_time,
            end_time=call_context.end_time,
            final_status=call_context.final_status,
            to_number=call_context.to_number,
            from_number=call_context.from_number
        )
        db.add(db_call_context)
        db.commit()
        db.refresh(db_call_context)
        return db_call_context

    def get_call_context(self, db: Session, call_sid: str):
        return db.query(CallContextModel).filter(CallContextModel.call_sid == call_sid).first()

    def update_call_context(self, db: Session, call_sid: str, call_context: CallContext):
        db_call_context = db.query(CallContextModel).filter(CallContextModel.call_sid == call_sid).first()
        if db_call_context:
            db_call_context.stream_sid = call_context.stream_sid
            db_call_context.call_ended = call_context.call_ended
            db_call_context.user_context = json.dumps(call_context.user_context)
            db_call_context.system_message = call_context.system_message
            db_call_context.initial_message = call_context.initial_message
            db_call_context.start_time = call_context.start_time
            db_call_context.end_time = call_context.end_time
            db_call_context.final_status = call_context.final_status
            db_call_context.to_number = call_context.to_number
            db_call_context.from_number = call_context.from_number
            db.commit()
            db.refresh(db_call_context)
        return db_call_context

    def delete_call_context(self, db: Session, call_sid: str):
        db_call_context = db.query(CallContextModel).filter(CallContextModel.call_sid == call_sid).first()
        if db_call_context:
            db.delete(db_call_context)
            db.commit()
        return db_call_context

    def get_all_call_contexts(self, db: Session):
        return db.query(CallContextModel).all()