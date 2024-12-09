from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import pandas as pd

# Define the database using SQLAlchemy
Base = declarative_base()

# Define tables
class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    translator = Column(String)
    book_format = Column(String)
    pages = Column(Integer)
    publisher = Column(String)
    published_date = Column(Date)
    year = Column(Integer)
    votes = Column(Integer)
    rating = Column(Float)
    checked_out = Column(Boolean, default=False)

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    group = Column(String, nullable=False)

class BorrowRecord(Base):
    __tablename__ = 'borrow_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    student = relationship("Student")
    book = relationship("Book")

# Initialize the SQLite database
engine = create_engine('sqlite:///library_management.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Populate the database with books from a CSV
def populate_books(data_path):
    data = pd.read_csv(data_path)
    for _, row in data.iterrows():
        # Check if the book already exists
        existing_book = session.query(Book).filter_by(isbn=row['isbn']).first()
        if existing_book is None:
            book = Book(
                isbn=row['isbn'],
                title=row['title'],
                author=row['author'],
                translator=row['translator'],
                book_format=row['format'],
                pages=row['pages'],
                publisher=row['publisher'],
                year=row['year'],
                votes=row['votes'],
                rating=row['rating'],
                checked_out=row['checked In/Out'].strip().lower() == 'out'
            )
            session.add(book)
    session.commit()

# Populate the database with students
def add_students():
    students = [
        {"first_name": "Alice", "last_name": "Smith", "group": "A"},
        {"first_name": "Bob", "last_name": "Johnson", "group": "B"},
        {"first_name": "Charlie", "last_name": "Brown", "group": "C"},
        {"first_name": "David", "last_name": "Williams", "group": "D"},
    ]
    for student in students:
        new_student = Student(
            first_name=student['first_name'],
            last_name=student['last_name'],
            group=student['group']
        )
        session.add(new_student)
    session.commit()

# Borrow a book
def borrow_book(student_name, book_title):
    session.expire_all()
    student = session.query(Student).filter(Student.first_name == student_name).first()
    book = session.query(Book).filter(Book.title == book_title).first()

    if book is None:
        print(f"The book '{book_title}' does not exist in the library.")
        return
    if student is None:
        print(f"The student '{student_name}' does not exist in the system.")
        return

    print(f"DEBUG: Book '{book_title}' checked_out status before borrowing: {book.checked_out}")

    if book.checked_out:
        print(f"The book '{book_title}' is already borrowed and cannot be borrowed again until returned.")
    else:
        record = BorrowRecord(
            student_id=student.id,
            book_id=book.id,
            borrow_date=date.today(),
            return_date=date.today() + timedelta(days=14)
        )
        book.checked_out = True
        session.add(record)
        session.commit()
        print(f"{student_name} borrowed {book_title}.")


# Return a book
def return_book(book_title):
    session.expire_all()
    book = session.query(Book).filter(Book.title == book_title, Book.checked_out == True).first()
    if book:
        book.checked_out = False
        session.commit()
        print(f"{book_title} has been returned.")
    else:
        print("Book not found or not checked out.")

# Find borrowed books for a student
def find_borrowed_books(student_name):
    session.expire_all()
    student = session.query(Student).filter(Student.first_name == student_name).first()
    if student:
        records = session.query(BorrowRecord).filter(BorrowRecord.student_id == student.id).all()
        if records:
            seen_books = set()
            for record in records:
                book = session.query(Book).filter(Book.id == record.book_id).first()
                if book.title not in seen_books:
                    print(f"{book.title} is borrowed and due on {record.return_date}.")
                    seen_books.add(book.title)
        else:
            print(f"No books borrowed by {student_name}.")
    else:
        print("Student not found.")

# Main Program
def main():
    data_path = '/Users/stanleyogbumuo/Downloads/COSC531_project/longlist3.csv' 
    populate_books(data_path)
    add_students()

    while True:
        print("\nLibrary Management System")
        print("1. Borrow a Book")
        print("2. Return a Book")
        print("3. Find Borrowed Books")
        print("4. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            student_name = input("Enter the student's first name: ")
            book_title = input("Enter the book title: ")
            borrow_book(student_name, book_title)
        elif choice == "2":
            book_title = input("Enter the book title to return: ")
            return_book(book_title)
        elif choice == "3":
            student_name = input("Enter the student's first name: ")
            find_borrowed_books(student_name)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

# Run the program
if __name__ == "__main__":
    main()
