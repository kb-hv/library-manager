from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import requests
from .models import Book, Transaction, Member
from . import db
from sqlalchemy.exc import SQLAlchemyError
import datetime

views_book = Blueprint("views_book", __name__)

@views_book.route("/")
@login_required
def home():
    try:
        # books in library
        filter_text = request.args.get("filter_text")
        filter_option = request.args.get("filter_option")
        books = []
        if filter_text:
            if filter_option == "title":
                books = Book.query.filter(Book.title.contains(filter_text))
            else:
                books = Book.query.filter(Book.authors.contains(filter_text))
        else:
            books = Book.query.all()
        return render_template("home.html", books=books, user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/import-books")
@login_required
def import_books():
    try:
        data = []
        if request.args.get("page_no"):
            page_no = request.args.get("page_no")
            filter_text = request.args.get("filter_text")
            filter_option = request.args.get("filter_option")
            url = "https://frappe.io/api/method/frappe-library?page=" + page_no
            if filter_option == "title":
                url += "&title=" + filter_text
            else:
                url += "&authors=" + filter_text
            headers = {
                "Cookie": "full_name=Guest; sid=Guest; system_user=no; user_id=Guest; user_image=https%3A//secure.gravatar.com/avatar/adb831a7fdd83dd1e2a309ce7591dff8%3Fd%3Dretro"
            }
            response = requests.request("GET", url, headers=headers, data={})

            if response.status_code == 200:
                data = response.json().get("message")
            else:
                flash("There was an error, please try again.", category="error")
            # return books from the API
        return render_template("import_books.html", books=data, user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/book")
@login_required
def retrieve_book_details():
    try:
        book_id = request.args.get("id")
        book = Book.query.filter_by(book_id=int(book_id)).first()
        return render_template("book_detail.html", book=book, user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/add-book", methods=["POST"])
@login_required
def add_books_to_library():
    try:
        book_data = request.form.get("book").split(";;")
        book_id = book_data[0]
        title = book_data[1]
        authors = book_data[2]
        publisher = book_data[3]
        publication_date = book_data[4]
        isbn13 = book_data[5]
        language_code = book_data[6]
        average_rating = book_data[7]

        # book already exists, add +1 to stock.
        existing_book = Book.query.filter_by(book_id=book_id).first()
        if existing_book:
            existing_book.stock += 1
            db.session.commit()
            flash(
                "Book "
                + existing_book.title
                + " already exists in your library. Added an extra copy! Current stock = "
                + str(existing_book.stock),
                category="success",
            )
        else:
            new_book = Book(
                book_id=book_id,
                title=title,
                authors=authors,
                publisher=publisher,
                stock=1,
                publication_date=publication_date,
                isbn13=isbn13,
                language_code=language_code,
                average_rating=average_rating,
            )
            db.session.add(new_book)
            db.session.commit()
            flash(
                "Book " + title + " has been added to your library.", category="success"
            )
        return render_template("import_books.html", user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/assign-book", methods=["POST"])
@login_required
def assign_book():
    try:

        origin = request.form.get("origin")
        email = request.form.get("email")
        book_id = request.form.get("book_id")
        member = Member.query.filter_by(email=email).first()
        book = Book.query.filter_by(book_id=book_id).first()

        if book and member:
            if member.outstanding_debt >= 500:
                flash(
                    "Member needs to clear dues before a book can be assigned",
                    category="error",
                )
                return redirect("/view-member?email=" + member.email)
            member.book_id = book.id
            new_transaction = Transaction(
                type="Book_Borrow",
                member_id=member.id,
                note="Borrowed " + book.title,
                book_id=book.id,
            )
            book.stock -= 1
            db.session.add(new_transaction)
            db.session.commit()
            flash(
                message="Assigned book "
                + book.title
                + " to "
                + member.full_name
                + ". Current stock = "
                + str(book.stock),
                category="success",
            )
        else:
            flash(message="Book/Member does not exist", category="error")
        if origin == "book":
            return redirect("/book?id=" + book_id)
        return redirect("/view-member?email=" + email)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/return-book", methods=["POST"])
@login_required
def return_book():
    try:

        member_id = request.form.get("member_id")
        member = Member.query.get(member_id)
        book = Book.query.get(member.book_id)

        # find borrow transaction to calculate due
        transaction = Transaction.query.filter_by(
            type="Book_Borrow", member_id=member_id, book_id=book.id
        ).first()
        date_delta = datetime.datetime.now() - transaction.date
        due_accrued = 5 + date_delta.days * 1
        member.outstanding_debt += due_accrued
        # transaction for book return
        new_transaction_return = Transaction(
            type="Book_Return",
            member_id=member.id,
            note="Returned " + book.title,
            book_id=book.id,
        )
        new_transaction_due = Transaction(
            type="Due_Accrued",
            member_id=member.id,
            note="Due accrued upon return of " + book.title,
            amount=due_accrued,
        )
        # add book back to library stock
        book.stock += 1
        # remove book from member
        member.book_id = None
        db.session.add(new_transaction_return)
        db.session.add(new_transaction_due)
        db.session.commit()
        flash(
            message="Returned book "
            + book.title
            + ". Due accrued = "
            + str(due_accrued)
            + ". Current stock = "
            + str(book.stock),
            category="success",
        )
        return redirect("/view-member?email=" + member.email)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_book.route("/remove-book", methods=["POST"])
@login_required
def remove_book():
    try:
        # check for borrowers
        book_id = request.form.get("book_id")
        book = Book.query.get(book_id)
        if book.members:
            flash(
                message="Some members have borrowed this book, can not be removed.",
                category="error",
            )
        else:
            db.session.delete(book)
            db.session.commit()
            flash(message="Book deleted.", category="success")
            return redirect(url_for("views_book.home"))
        return redirect("/book?id=" + str(book.book_id))
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)
