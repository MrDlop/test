import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    telegram_id = sqlalchemy.Column(sqlalchemy.Integer,
                                    primary_key=True, autoincrement=True, unique=True)
    company_id = sqlalchemy.Column(sqlalchemy.Integer,
                                   sqlalchemy.ForeignKey("companies.company_id"))
    company = orm.relationship('Company')
    prompt = sqlalchemy.Column(sqlalchemy.String, default=" ")
