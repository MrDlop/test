import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class CompanyUser(SqlAlchemyBase):
    __tablename__ = 'companies_users'
    ID = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, )
    company_id = sqlalchemy.Column(sqlalchemy.Integer)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer)
