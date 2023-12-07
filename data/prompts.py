import sqlalchemy
from .db_session import SqlAlchemyBase


class Prompt(SqlAlchemyBase):
    __tablename__ = 'prompts'

    prompt = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    description = sqlalchemy.Column(sqlalchemy.String)
