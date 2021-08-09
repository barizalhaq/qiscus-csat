import enum

from .extensions import db
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import backref


class BaseModel(db.Model):
    """
    Abstract Model.
    Define the base model for all other models.
    """

    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def as_dict(self):
        """Return data as python dictionary."""

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def save(self):
        """Save an instance of the model from the database."""

        try:
            db.session.add(self)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        except SQLAlchemyError:
            db.session.rollback()

    def update(self):
        """Update an instance of the model from the database."""

        return db.session.commit()

    def delete(self):
        """Delete an instance of the model from the database."""

        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()


class RatingType(enum.Enum):
    STAR = 1
    NUMBER = 2
    CUSTOM = 3
    EMOJI = 4


class App(BaseModel):
    __tablename__ = "apps"

    app_code = db.Column(db.String, nullable=False)
    app_name = db.Column(db.String, nullable=False)
    admin_email = db.Column(db.String, nullable=False)
    admin_token = db.Column(db.String, nullable=False)

    def __repr__(self):
        return "<App id:{}>".format(self.id)

    @classmethod
    def get_by_code(cls, app_code):
        return cls.query.filter_by(app_code=app_code).first()

    def create_default_config(self):
        Config.default(self.id)


class Config(BaseModel):
    __tablename__ = "configs"

    official_web = db.Column(db.String, nullable=True)
    csat_msg = db.Column(db.String, nullable=False)
    rating_type = db.Column(db.Enum(RatingType), nullable=True)
    rating_total = db.Column(db.Integer, nullable=True)
    extras = db.Column(db.String, nullable=True)
    csat_page = db.Column(db.String, nullable=True)

    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False)
    app = db.relationship("App", backref=backref("config", uselist=False))

    def __repr__(self):
        return "<Config id:{}>".format(self.id)

    @classmethod
    def get_by_app_id(cls, app_id):
        return cls.query.filter_by(app_id=app_id).first()

    @classmethod
    def default(cls, app_id):
        default_config = cls(
            csat_msg="Agar kami dapat terus meningkatkan pelayanan kepada pelanggan, mohon kesediaannya meluangkan waktu untuk mengisi survey dengan klik link berikut *{link}*. Terima kasih",
            official_web="https://qiscus.com",
            rating_type=None,
            rating_total=None,
            extras=None,
            app_id=app_id,
            csat_page=None
        )
        try:
            db.session.add(default_config)
            db.session.commit()
        except SQLAlchemyError as err:
            db.session.rollback()
            raise err


class Csat(BaseModel):
    __tablename__ = "csats"

    csat_code = db.Column(db.String, nullable=False)
    user_id = db.Column(db.String, nullable=False)
    rating = db.Column(db.String, nullable=True)
    feedback = db.Column(db.String, nullable=True)
    agent_email = db.Column(db.String, nullable=False)
    source = db.Column(db.String, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)

    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False)
    app = db.relationship("App", backref="satisfactions")

    def __repr__(self):
        return "<Satisfaction id:{}>".format(self.id)

    @classmethod
    def get_by_csat_code(cls, csat_code):
        return cls.query.filter_by(csat_code=csat_code).first()
