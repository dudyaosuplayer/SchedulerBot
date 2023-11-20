from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

engine = create_engine('sqlite:///polls.db', echo=True)
Base = declarative_base()


# Определение таблицы poll
class Poll(Base):
    __tablename__ = 'poll'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    absent = Column(Integer)
    attend = Column(Integer)
    date = Column(DateTime)
    chat_id = Column(Integer)

    user = relationship('User', back_populates='poll')

    def __repr__(self):
        return f"<Poll(id={self.id}, question={self.question}, is_anonymous={self.is_anonymous}, option_1={self.option_1}, option_2={self.option_2})>"


# Определение таблицы user
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    absenteeism = Column(Integer)
    visits = Column(Integer)
    poll_id = Column(Integer, ForeignKey('poll.id'), primary_key=True)

    poll = relationship('Poll', back_populates='user')

    def __repr__(self):
        return f"<User(id={self.id}, poll_id={self.poll_id}, name={self.name}, absenteeism={self.absenteeism}, visits={self.visits})>"


Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
