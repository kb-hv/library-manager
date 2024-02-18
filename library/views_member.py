from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Book, Transaction, Member
from . import db
from sqlalchemy.exc import SQLAlchemyError

views_member = Blueprint("views_member", __name__)

@views_member.route("/members", methods=["POST", "GET"])
@login_required
def members():
    return render_template("members.html", user=current_user)


@views_member.route("/add-member", methods=["POST"])
@login_required
def add_member():
    try:
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        # check for existing member
        member = Member.query.filter_by(email=email).first()
        if member:
            flash("Member already exists.", category="error")
        else:
            new_member = Member(email=email, full_name=full_name, outstanding_debt=500)
            db.session.add(new_member)
            db.session.commit()
            new_transaction = Transaction(
                amount=500,
                type="Due_Accrued",
                member_id=new_member.id,
                note="Membership fee",
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash("Member added successfully", category="success")
            return render_template("members.html", user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_member.route("/view-member")
@login_required
def view_member():
    try:
        email = request.args.get("email")
        member = Member.query.filter_by(email=email).first()
        if member:
            if member.book_id:
                book = Book.query.filter_by(id=member.book_id).first()
                member.book = book
            member.transactions.sort(key=lambda r: r.date, reverse=True)
            return render_template(
                "member_detail.html", member=member, user=current_user
            )
        else:
            flash("Member does not exist", category="error")
        return render_template("members.html", member=[], user=current_user)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_member.route("/pay-dues", methods=["POST"])
@login_required
def pay_dues():
    try:
        amount = int(request.form.get("amount"))
        member_id = request.form.get("member_id")
        member = Member.query.get(member_id)
        if member.outstanding_debt < amount:
            flash(message="Amount is greater than outstanding due.", category="error")
        elif amount < 1:
            flash(message="Minimum amount is Rs 1.", category="error")
        else:
            member.outstanding_debt -= amount
            new_transaction = Transaction(
                type="Due_Payment",
                member_id=member.id,
                note="Due paid " + str(amount),
                amount=amount,
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash(message="Due paid successfully", category="success")
        return redirect("/view-member?email=" + member.email)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)


@views_member.route("/remove-member", methods=["POST"])
@login_required
def remove_member():
    try:
        # check for borrowed books and outstanding debt
        member_id = request.form.get("member_id")
        member = Member.query.get(member_id)
        if member.outstanding_debt and member.outstanding_debt > 0:
            flash(
                message="Member still has outstanding dues, can not be deleted.",
                category="error",
            )
        elif member.book_id != None:
            flash(
                message="Member still has a borrowed book, can not be deleted.",
                category="error",
            )
        else:
            db.session.delete(member)
            db.session.commit()
            flash(message="Member deleted.", category="success")
            return redirect(url_for("views_member.members"))
        return redirect("/view-member?email=" + member.email)
    except SQLAlchemyError as e:
        flash(
            "There was an error, please try again. (" + str(e.orig) + ")",
            category="error",
        )
        return render_template("home.html", user=current_user)
