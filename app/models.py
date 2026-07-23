from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False)
    number = Column(Integer, nullable=False)
    industry = Column(String, nullable=False)
    profession = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)

    sub_agents = relationship("SubAgent", back_populates="agent")


class SubAgent(Base):
    __tablename__ = "sub_agents"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    slug = Column(String, nullable=False)
    name = Column(String, nullable=False)
    task = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)

    agent = relationship("Agent", back_populates="sub_agents")

    __table_args__ = (UniqueConstraint("agent_id", "slug"),)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (UniqueConstraint("email", "agent_id"),)  # per-agent isolation


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    sub_agent_id = Column(Integer, ForeignKey("sub_agents.id"), nullable=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    tokens = Column(Integer, nullable=False, default=0)