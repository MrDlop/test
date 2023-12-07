import sqlalchemy
from .db_session import SqlAlchemyBase


class Message(SqlAlchemyBase):
    __tablename__ = 'messages'

    ID = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer,
                                    autoincrement=True)
    company_id = sqlalchemy.Column(sqlalchemy.Integer,
                                   autoincrement=True)
    request = sqlalchemy.Column(sqlalchemy.String)
    response = sqlalchemy.Column(sqlalchemy.String)
