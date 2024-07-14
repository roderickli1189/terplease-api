from config import db
from sqlalchemy import CheckConstraint
from sqlalchemy import ARRAY
import datetime

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    apartment = db.Column(db.String(50), unique=False, nullable=False)
    rent = db.Column(db.Integer, CheckConstraint('rent >= 0 AND rent <= 5000'), unique=False, nullable=False)
    lay_out = db.Column(db.String(50), unique=False, nullable=False)
    description = db.Column(db.String(250), unique=False, nullable=True)
    gender = db.Column(db.String(50), unique=False, nullable=True)
    semester = db.Column(db.String(50), unique=False, nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    post_date = db.Column(db.DateTime, nullable=False)
    images = db.Column(ARRAY(db.String), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def to_json(self):
        return {
            "id": self.id,
            "apartment": self.apartment,
            "rent": self.rent,
            "layOut": self.lay_out,
            "description": self.description,
            "gender": self.gender,
            "semester": self.semester,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "postDate": self.post_date,
            "images": self.images,
            "user": {
                "name": self.user.name,  # Assuming username is equivalent to name
                "email": self.user.email,
                "picture": self.user.picture,
                "nickname": self.user.nickname,
                "phoneNumber": self.user.phone_number,
            } if self.user else None,
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), unique=False, nullable=False)
    nickname = db.Column(db.String(), unique=False, nullable=True)
    sub = db.Column(db.String(), unique=False, nullable=False)
    email = db.Column(db.String(), unique=True, nullable=False)
    picture = db.Column(db.String(), unique=True, nullable=False)
    phone_number = db.Column(db.String(), unique=True, nullable=True)
    listings = db.relationship('Listing', backref="user")

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "sub": self.sub,
            "email": self.email,
            "picture": self.picture,
            "listings": [listing.to_json() for listing in self.listings],
            "phoneNumber": self.phone_number,
            "nickname": self.nickname,

        }
    
    def get_listing(self):
        return {
            "listings": [listing.to_json() for listing in self.listings]
        }