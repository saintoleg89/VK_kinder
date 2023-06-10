import sqlalchemy as sq
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from settings import db_pass, db_admin, db_name, db_host

Base = declarative_base()

engine = sq.create_engine(f'postgresql+psycopg2://{db_admin}:{db_pass}@{db_host}/{db_name}')
Session = sessionmaker(bind=engine)
if not database_exists(engine.url):
    create_database(engine.url)
    print('База данных бота создана...')


class DatingUser(Base):
    __tablename__ = 'DatingUser'

    dating_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    bdate = sq.Column(sq.String)
    age_min = sq.Column(sq.Integer)
    age_max = sq.Column(sq.Integer)
    city_name = sq.Column(sq.String)
    city_id = sq.Column(sq.Integer)
    sex = sq.Column(sq.Integer)
    partners_sex = sq.Column(sq.Integer)
    matchingusers = relationship('MatchingUser', backref='DatingUser')
    blacklistedusers = relationship('BlacklistedUser', backref='DatingUser')


class MatchingUser(Base):
    __tablename__ = 'MatchingUser'

    matching_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    bdate = sq.Column(sq.String)
    id_dater = sq.Column(sq.Integer,sq.ForeignKey('DatingUser.dating_id'))
    photos = relationship('Photos', backref='MatchingUser')
    sex = sq.Column(sq.Integer)


class Photos(Base):
    __tablename__ = 'Photos'

    photo_id = sq.Column(sq.Integer, primary_key=True)
    id_matcher = sq.Column(sq.Integer, sq.ForeignKey('MatchingUser.matching_id'))
    photo_link = sq.Column(sq.String)
    likes_count = sq.Column(sq.Integer)


class BlacklistedUser(Base):
    __tablename__ = 'BlacklistedUser'

    blacklisted_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    id_dater = sq.Column(sq.Integer,sq.ForeignKey('DatingUser.dating_id'))

def database_check(check_id):
    """
    Проверка на вхождение в БД
    """
    session = Session()

    liked_users = session.query(MatchingUser).all()
    liked_users_list = [liked_user.matching_id for liked_user in liked_users]

    disliked_users = session.query(BlacklistedUser).all()
    disliked_users_list = [disliked_user.blacklisted_id for disliked_user in disliked_users]

    if check_id in liked_users_list or check_id in disliked_users_list:
        return True
    else:
        return False

if __name__ == '__main__':
    Base.metadata.create_all(engine)



