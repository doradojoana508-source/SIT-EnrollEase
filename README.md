# SIT-EnrollEase

**SIT Integrated Enrollment and Student Records System**

SIT-EnrollEase is a web-based enrollment and student records management system developed for the Simons Institute of Theology (SIT). It aims to improve the management of student information, enrollment processes, academic records, and related administrative tasks.

## Project Overview

The system was developed to help reduce manual recordkeeping and make student information more organized and accessible to authorized users.

### Technologies Used

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript, Bootstrap, Jinja2
- **Database:** MySQL
- **Database Environment:** XAMPP
- **Security:** Flask-WTF CSRF protection
- **Email:** Flask-Mail

## Features

- Student information management
- Enrollment management
- Academic records management
- Curriculum and subject management
- Student schedules
- Administrative reports
- User authentication and access control

*Note: Available features depend on the implemented modules and user permissions.*

## Requirements

Before running the project, install the following:

- Python 3.10 or later
- XAMPP
- MySQL
- Git

## Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd SIT-EnrollEase
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database

1. Open XAMPP Control Panel.
2. Start Apache and MySQL.
3. Open phpMyAdmin at `http://localhost/phpmyadmin`.
4. Create the database using the database name configured in the project.
5. Import the provided `schema.sql` file.

### 5. Configure the Application

Use `config.example.py` as a reference for your local configuration.

Create or update your local `config.py` with the appropriate database connection settings and other required configuration values.

Do not upload passwords, email credentials, secret keys, or other sensitive configuration values to GitHub.

### 6. Initialize the Database

After importing `schema.sql`, run:

```bash
python seed.py
```

This initializes the database with the project's initial data.

### 7. Run the Application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Database Initialization Order

Follow this order when setting up the database:

1. Import `schema.sql` into MySQL.
2. Run `python seed.py`.

## Project Structure

```text
SIT-EnrollEase/
│
├── app.py
├── config.example.py
├── db.py
├── errors.py
├── mailer.py
├── menus.py
├── requirements.txt
├── schema.sql
├── seed.py
├── seed_curriculum.py
│
├── migrations/
├── models/
├── routes/
├── static/
└── templates/
```

## Client Information

**Client:** Simons Institute of Theology (SIT)

The project was developed based on the client's requirements and feedback regarding enrollment processes, student information management, academic records, and administrative reporting.

## Developer

**Developer:** Joana Dorado  
**Program:** Bachelor of Science in Information Technology  
**University:** Laguna University

## Important Notes

- Use your own local database credentials and configuration.
- Keep sensitive information out of the public repository.
- Ensure that all required project files are included before deployment or submission.
- This project is intended for academic and institutional use.

## License

This project was developed as an academic project for the Simons Institute of Theology.
