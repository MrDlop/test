import datetime
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash
from .db_session import SqlAlchemyBase


class Company(SqlAlchemyBase):
    __tablename__ = 'companies'

    company_id = sqlalchemy.Column(sqlalchemy.Integer,
                                   primary_key=True, autoincrement=True)
    time = sqlalchemy.Column(sqlalchemy.DateTime,
                             default=datetime.datetime.now)
    company_name = sqlalchemy.Column(sqlalchemy.String,
                                     unique=True, index=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String,
                                        nullable=True)
    max_num_users = sqlalchemy.Column(sqlalchemy.Integer)

    def __init__(self, company_id: int, company_name: str, max_num_users: int, time: str):
        self.company_id = company_id
        self.company_name = company_name
        self.time = datetime.datetime.strptime(time, "%d.%m.%y")
        self.max_num_users = max_num_users

    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)

    def set_time(self, time: str) -> None:
        self.time = datetime.datetime.strptime(time, "%d.%m.%y")

