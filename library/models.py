from . import db
from flask_login import UserMixin
from sqlalchemy import Enum, func
import enum

class TransactionTypes(enum.Enum):
  Due_Accrued = 1
  Due_Payment = 2
  Book_Borrow = 3
  Book_Return = 4

class Transaction(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  amount = db.Column(db.Integer)
  type = db.Column(Enum(TransactionTypes))
  book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
  member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
  note = db.Column(db.String(10000))
  date = db.Column(db.DateTime(timezone=True), default=func.now())

class Member(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  email = db.Column(db.String(150), unique = True)
  full_name = db.Column(db.String(10000))
  outstanding_debt = db.Column(db.Integer)
  book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
  transactions = db.relationship('Transaction')

class Book(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  book_id = db.Column(db.Integer, unique = True)
  title = db.Column(db.String(10000))
  authors = db.Column(db.String(10000))
  stock = db.Column(db.Integer)
  publisher = db.Column(db.String(10000))
  transactions = db.relationship('Transaction')
  publication_date = db.Column(db.String(10000))
  isbn13 = db.Column(db.String(10000))
  language_code = db.Column(db.String(10000))
  average_rating = db.Column(db.Double)
  members = db.relationship('Member')

class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key = True)
  email = db.Column(db.String(150), unique = True)
  password = db.Column(db.String(150))