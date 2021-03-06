import os
from datetime import datetime

import smtplib
from email.mime.multipart import MIMEMultipart  # Многокомпонентный объект
from email.mime.text import MIMEText

from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash
from flask_login import login_required, current_user
from sqlalchemy import null
from werkzeug.utils import secure_filename

from . import db
from .models import Item
from . import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

main = Blueprint('main', __name__)


def send_email(addr_to, body):
    addr_from = "79506450150@yandex.ru"
    addr_to = "bucholzevb@mail.ru"
    password_em = '12345bogdanliza'

    msg = MIMEMultipart()
    msg['From'] = addr_from  # Адресат
    msg['To'] = addr_to
    msg['Subject'] = 'Ставка сделана, милорд'

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
    server.login(addr_from, password_em)
    server.send_message(msg)
    server.quit()


@main.route('/')
def index():
    item = Item.query.all()
    return render_template('main_menu.html', data=item)


@main.route('/profile')
@login_required
def profile():
    item = Item.query.all()
    return render_template('profile.html', data=item)


@main.route('/offer', methods=['POST'])
def offer_post():
    title = request.form.get('title')
    price = request.form.get('price')
    final_date = request.form.get('final_date')
    description = request.form.get('description')

    if len(title) < 1 or len(price) < 1 or len(final_date) < 1:
        flash("Заполните все поля")
        return redirect(url_for('main.offer'))

    new_item = Item(title=title, price=price, final_date=final_date, user=current_user, description=description)

    db.session.add(new_item)
    db.session.commit()

    return redirect(url_for('main.profile'))


@main.route('/offer', methods=['GET'])
@login_required
def offer():
    return render_template('offer.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/uploads', methods=['GET', 'POST'])
def upload_file():
    item = Item.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, str(item.id) + ".png"))

            return redirect(url_for('main.uploaded_file', name=item.id))
    return '''
       <!doctype html>
       <title>Загрузите файл</title>
       <h1>Upload new File</h1>
       <form method=post enctype=multipart/form-data>
         <input type=file name=file>
         <input type=submit value=Upload>
       </form>
       '''


@main.route('/items/<name>')
def uploaded_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)


@main.route('/own')
def own_lots():
    item = Item.query.filter_by(user_id=current_user.id)
    return render_template('my_items.html', data=item)


@main.route('/buy/<int:id>', methods=['GET', 'POST'])
@login_required
def buy(id):
    item = Item.query.filter_by(id=id).first()
    dt = str(datetime.fromisoformat(item.final_date))[:-3]
    delta = datetime(int(dt[0:4]), int(dt[5:7]), int(dt[8:10])) - datetime.now()
    final_delta = str(delta.days) + " дней ", str(delta.seconds // 3600) + " часов ", str(
        (delta.seconds // 60) % 60) + " минут ", str(delta.seconds % 60) + " секунд "
    final_delta = ''.join(final_delta)
    if request.method == "POST":
        new_price = request.form.get('price')
        mail = request.form.get('mail')
        if int(new_price) > item.price:
            setattr(item, 'price', new_price)
            setattr(item, 'buyer', current_user.name)

            db.session.commit()
            send_email(mail, f"Ваша ставка зарегистрирована! Товар {item.title} будет доступен по цене {item.price} рублей по истечении срока лота, если вашу ставку никто не перебьет. Осталось {final_delta}")

        else:
            flash("Я все понимаю, но цена должна быть больше стартовой")

        return redirect('/')
    else:


        dts = dt[8:10] + '-' + dt[5:7] + '-' + dt[0:4] + "  00:00"
        return render_template('buy.html', data=item, dt=final_delta)


@main.route('/info/<int:id>')
def info(id):
    item = Item.query.filter_by(id=id)

    return render_template('info.html', item=item)


@main.route('/change/<int:num>', methods=['GET'])
@login_required
def change_get(num):
    item = Item.query.filter_by(id=num).first()
    return render_template("change.html", data=item)


@main.route('/change/<int:num>', methods=['POST'])
@login_required
def change(num):
    items_id = Item.query.filter_by(user_id=current_user.id).all()
    title = request.form.get('title')
    price = request.form.get('price')
    final_date = request.form.get('final_date')
    description = request.form.get('description')
    item = Item.query.filter_by(id=num).first()

    new_item = Item(title=title, price=price, final_date=final_date, description=description, user=current_user)
    if item in items_id:
        db.session.delete(item)
        db.session.add(new_item)
        db.session.commit()
        return redirect('/')

    else:
        flash('У вас нет доступа к чужим объявлениям')
        return redirect(url_for("main.profile"))
