from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema

from app.models.book import BookAssignment
from app.models.user import User
from app.config.email import conf

async def send_due_soon_reminders(db: Session):
    today = datetime.now()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)
    assignments = db.query(BookAssignment).filter(
        BookAssignment.due_date >= start,
        BookAssignment.due_date < end,
        BookAssignment.returned_at == None
    ).all()
    fm = FastMail(conf)
    for assignment in assignments:
        user = db.query(User).filter(User.id == assignment.user_id).first()
        message = MessageSchema(
            subject="Book Return Reminder",
            recipients=[user.email],
            body=f"Dear {user.username},\n\nThis is a reminder to return your borrowed book (ID: {assignment.book_id}) by {assignment.due_date.strftime('%Y-%m-%d')}.",
            subtype="plain",
        )
        await fm.send_message(message)
