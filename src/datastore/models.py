from datetime import datetime
from enum import IntEnum
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKeyConstraint

from src.datastore import db
from src.utils import generate_id


class ProgressStatus(IntEnum):
    FAILED = 0
    DONE = 1
    PENDING = 2
    NOTIFYING = 3


class Review(db.Model):
    url = db.Column(db.String, primary_key=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    location = db.Column(db.String, nullable=True)
    reviewer = db.Column(db.String, nullable=True)
    content = db.Column(db.Text, nullable=True)


class Request(db.Model):
    id = db.Column(db.String, primary_key=True, default=generate_id)
    email = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    progress = relationship("Progress", cascade="all, delete-orphan", passive_deletes=True)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    url = db.Column(db.Integer, db.ForeignKey('review.url'), nullable=False)
    status = db.Column(db.Integer, default=ProgressStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Define composite foreign key constraint
    __table_args__ = (
        ForeignKeyConstraint(['request_id'], ['request.id'], ondelete='CASCADE'),
    )
