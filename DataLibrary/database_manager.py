import json
import os
from datetime import datetime

from sqlalchemy import Column, String, Boolean, Text, DateTime, Integer, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


class DatabaseManager:
    """
    DatabaseManager is a class that manages the database operations for call contexts and transcriptions.

    Args:
        db_url (str): The URL of the database. Default is "sqlite+aiosqlite:///./DataLibrary/call_contexts.db".

    Attributes:
        engine (alchemy.AsyncEngine): The SQLAlchemy async engine for the database connection.
        SessionLocal (alchemy.orm.session.Session): The SQLAlchemy async session for the database.
        Base (alchemy.ext.declarative.api.DeclarativeMeta): The SQLAlchemy declarative base for table definitions.
        ContactModel (alchemy.ext.declarative.api.DeclarativeMeta): The SQLAlchemy model class for contacts table.
        CallContextModel (alchemy.ext.declarative.api.DeclarativeMeta): The SQLAlchemy model class for call_contexts table.
        TranscriptionModel (alchemy.ext.declarative.api.DeclarativeMeta): The SQLAlchemy model class for transcriptions table.

    Methods:
        _initialize_tables(): Initializes the tables in the database.
        get_db(): Creates a database session and yields it for use.
        create_call_context(db: AsyncSession, call_context): Creates a new call context in the database.
        get_call_context(db: AsyncSession, call_sid: str): Retrieves a call context based on the call SID.
        update_call_context(db: AsyncSession, call_sid: str, call_context): Updates a call context in the database.
        delete_call_context(db: AsyncSession, call_sid: str): Deletes a call context from the database.
        get_all_call_contexts(db: AsyncSession): Retrieves all call contexts from the database.
        create_transcription(db: AsyncSession, call_sid: str, transcription_text: str): Creates a new transcription in the database.
        get_transcription(db: AsyncSession, call_sid: str): Retrieves a transcription based on the call SID.
        delete_transcription(db: AsyncSession, call_sid: str): Deletes a transcription from the database.
        get_all_contacts(db: AsyncSession): Retrieves all contacts from the database.
        get_contact_by_phone(db: AsyncSession, phone_number: str): Retrieves a contact based on the phone number.
    """
    def __init__(self, db_url: str = "sqlite+aiosqlite:///./DataLibrary/call_contexts.db"):
        # Ensure the DataLibrary folder exists
        if not os.path.exists('DataLibrary'):
            os.makedirs('DataLibrary')

        # SQLAlchemy async setup with aiosqlite
        self.engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, class_=AsyncSession)
        self.Base = declarative_base()

        # Initialize the tables
        self._initialize_tables()

    def _initialize_tables(self):
        class ContactModel(self.Base):
            __tablename__ = "contacts"

            contact_id = Column(Integer, primary_key=True, index=True)
            phone_number = Column(String, unique=True, nullable=False)
            created_at = Column(DateTime, default=datetime.utcnow)

            # Relationship to Calls
            calls = relationship("CallContextModel", back_populates="contact")

        class CallContextModel(self.Base):
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

            # Foreign key to ContactModel
            contact_id = Column(Integer, ForeignKey('contacts.contact_id'))
            contact = relationship("ContactModel", back_populates="calls")

            # Relationship to Transcriptions
            transcription = relationship("TranscriptionModel", back_populates="call", uselist=False)

        class TranscriptionModel(self.Base):
            __tablename__ = "transcriptions"

            transcription_id = Column(Integer, primary_key=True, index=True)
            call_id = Column(String, ForeignKey('call_contexts.call_sid'), nullable=False)
            transcription_text = Column(Text, nullable=False)
            created_at = Column(DateTime, default=datetime.utcnow)

            # Relationship to CallContext
            call = relationship("CallContextModel", back_populates="transcription")

        # Save these classes as attributes of the DatabaseManager class
        self.ContactModel = ContactModel
        self.CallContextModel = CallContextModel
        self.TranscriptionModel = TranscriptionModel

        # Create the database tables
        async def create_tables():
            async with self.engine.begin() as conn:
                await conn.run_sync(self.Base.metadata.create_all)

        import asyncio
        asyncio.run(create_tables())

    async def get_db(self):
        async with self.SessionLocal() as db:
            try:
                yield db
            finally:
                await db.close()

    async def create_call_context(self, db: AsyncSession, call_context):
        db_call_context = self.CallContextModel(
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
            from_number=call_context.from_number,
            contact_id=call_context.contact_id
        )
        db.add(db_call_context)
        await db.commit()
        await db.refresh(db_call_context)
        return db_call_context

    async def get_call_context(self, db: AsyncSession, call_sid: str):
        return await db.query(self.CallContextModel).filter(self.CallContextModel.call_sid == call_sid).first()

    async def update_call_context(self, db: AsyncSession, call_sid: str, call_context):
        db_call_context = await db.query(self.CallContextModel).filter(
            self.CallContextModel.call_sid == call_sid).first()
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
            db_call_context.contact_id = call_context.contact_id
            await db.commit()
            await db.refresh(db_call_context)
        return db_call_context

    async def delete_call_context(self, db: AsyncSession, call_sid: str):
        db_call_context = await db.query(self.CallContextModel).filter(
            self.CallContextModel.call_sid == call_sid).first()
        if db_call_context:
            await db.delete(db_call_context)
            await db.commit()
        return db_call_context

    async def get_all_call_contexts(self, db: AsyncSession):
        return await db.query(self.CallContextModel).all()

    async def create_transcription(self, db: AsyncSession, call_sid: str, transcription_text: str):
        db_transcription = self.TranscriptionModel(
            call_id=call_sid,
            transcription_text=transcription_text
        )
        db.add(db_transcription)
        await db.commit()
        await db.refresh(db_transcription)
        return db_transcription

    async def get_transcription(self, db: AsyncSession, call_sid: str):
        return await db.query(self.TranscriptionModel).filter(self.TranscriptionModel.call_id == call_sid).first()

    async def delete_transcription(self, db: AsyncSession, call_sid: str):
        db_transcription = await db.query(self.TranscriptionModel).filter(
            self.TranscriptionModel.call_id == call_sid).first()
        if db_transcription:
            await db.delete(db_transcription)
            await db.commit()
        return db_transcription

    async def get_all_contacts(self, db: AsyncSession):
        return await db.query(self.ContactModel).all()

    async def get_contact_by_phone(self, db: AsyncSession, phone_number: str):
        return await db.query(self.ContactModel).filter(self.ContactModel.phone_number == phone_number).first()


# Example usage of the DatabaseManager class:
if __name__ == "__main__":
    db_manager = DatabaseManager()


    # Example of using the DatabaseManager class in an async context
    async def main():
        """
        Main Method

        This method is used to create a new contact and a new call context in the database.

        :return: None
        """
        async with db_manager.SessionLocal() as db:
            # Create a new contact
            new_contact = db_manager.ContactModel(phone_number="1234567890")
            db.add(new_contact)
            await db.commit()

            # Create a new call context
            new_call_context = db_manager.CallContextModel(
                call_sid="ABC123",
                stream_sid="STREAM123",
                call_ended=False,
                user_context=json.dumps(["user_action"]),
                system_message="System message",
                initial_message="Hello",
                start_time=datetime.utcnow(),
                end_time=None,
                final_status="in_progress",
                to_number="1234567890",
                from_number="0987654321",
                contact_id=new_contact.contact_id
            )
            db.add(new_call_context)
            await db.commit()


    import asyncio

    asyncio.run(main())
