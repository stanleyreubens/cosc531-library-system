@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        student_name = request.form['student_name']
        book_title = request.form['book_title']
        student = session.query(Student).filter_by(first_name=student_name).first()
        book = session.query(Book).filter_by(title=book_title).first()

        if not student:
            flash(f"Student '{student_name}' not found!")
            return redirect(url_for('borrow'))
        if not book:
            flash(f"Book '{book_title}' not found!")
            return redirect(url_for('borrow'))
        if book.checked_out:
            flash(f"Book '{book_title}' is already borrowed!")
            return redirect(url_for('borrow'))

        record = BorrowRecord(
            student_id=student.id,
            book_id=book.id,
            borrow_date=date.today(),
            return_date=date.today() + timedelta(days=14)
        )
        book.checked_out = True
        session.add(record)
        session.commit()
        flash(f"'{book_title}' successfully borrowed by {student_name}!")
        return redirect(url_for('index'))

    return render_template('borrow.html')

@app.route('/return', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        book_title = request.form['book_title']
        book = session.query(Book).filter_by(title=book_title).first()

        if not book:
            flash(f"Book '{book_title}' not found!")
            return redirect(url_for('return_book'))
        if not book.checked_out:
            flash(f"Book '{book_title}' is not borrowed!")
            return redirect(url_for('return_book'))

        book.checked_out = False
        session.commit()
        flash(f"'{book_title}' successfully returned!")
        return redirect(url_for('index'))

    return render_template('return.html')

@app.route('/find', methods=['GET', 'POST'])
def find():
    borrowed_books = []
    if request.method == 'POST':
        student_name = request.form['student_name']
        student = session.query(Student).filter_by(first_name=student_name).first()

        if not student:
            flash(f"Student '{student_name}' not found!")
            return redirect(url_for('find'))

        records = (
            session.query(BorrowRecord)
            .filter_by(student_id=student.id)
            .all()
        )

        for record in records:
            borrowed_books.append((record.book.title, record.return_date))

    return render_template('find.html', borrowed_books=borrowed_books)