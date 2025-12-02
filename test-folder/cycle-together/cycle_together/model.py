import datetime
import enum
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Text, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import flask_login
from . import db


class TripStatus(enum.Enum):
    open = 1
    closed_to_new = 2
    finalized = 3
    cancelled = 4


class DifficultyLevel(enum.Enum):
    beginner = 1
    intermediate = 2
    advanced = 3
    expert = 4


class User(flask_login.UserMixin, db.Model):
    __tablename__ = 'user'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    password: Mapped[str] = mapped_column(String(256))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    created_trips: Mapped[List["TripProposal"]] = relationship(back_populates="creator")
    participations: Mapped[List["TripParticipation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship(back_populates="author")
    created_meetups: Mapped[List["Meetup"]] = relationship(back_populates="creator")


class TripProposal(db.Model):
    __tablename__ = 'trip_proposal'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(512))
    
    departure_location: Mapped[str] = mapped_column(String(128))
    destination: Mapped[str] = mapped_column(String(128))
    route_description: Mapped[Optional[str]] = mapped_column(Text)
    distance_km: Mapped[float] = mapped_column(Float)
    difficulty: Mapped[DifficultyLevel]
    
    start_date_min: Mapped[datetime.date] = mapped_column(Date)
    start_date_max: Mapped[datetime.date] = mapped_column(Date)
    duration_days_min: Mapped[int] = mapped_column(Integer)
    duration_days_max: Mapped[int] = mapped_column(Integer)
    
    budget_per_person: Mapped[float] = mapped_column(Float)
    max_participants: Mapped[int] = mapped_column(Integer)
    status: Mapped[TripStatus]
    
    departure_final: Mapped[bool] = mapped_column(Boolean, default=False)
    destination_final: Mapped[bool] = mapped_column(Boolean, default=False)
    dates_final: Mapped[bool] = mapped_column(Boolean, default=False)
    route_final: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_final: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    
    creator: Mapped["User"] = relationship(back_populates="created_trips")
    participations: Mapped[List["TripParticipation"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    meetups: Mapped[List["Meetup"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class TripParticipation(db.Model):
    __tablename__ = 'trip_participation'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"))
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    user: Mapped["User"] = relationship(back_populates="participations")
    trip: Mapped["TripProposal"] = relationship(back_populates="participations")


class Message(db.Model):
    __tablename__ = 'message'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"))
    
    author: Mapped["User"] = relationship(back_populates="messages")
    trip: Mapped["TripProposal"] = relationship(back_populates="messages")


class Meetup(db.Model):
    __tablename__ = 'meetup'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    location: Mapped[str] = mapped_column(String(256))
    meetup_datetime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    
    trip: Mapped["TripProposal"] = relationship(back_populates="meetups")
    creator: Mapped["User"] = relationship(back_populates="created_meetups")