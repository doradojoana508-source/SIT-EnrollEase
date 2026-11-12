# SIT-EnrollEase

### SIT Integrated Enrollment and Student Records System

SIT-EnrollEase is a web-based enrollment and student records management system developed for **Simons Institute of Theology (SIT)**. It aims to improve the management of student information, enrollment processes, academic records, and related administrative tasks.

## Project Overview

The system was developed to help reduce manual recordkeeping and make student information more organized and accessible to authorized users.

## Technologies Used

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

Before running the project, install:

- Python
- XAMPP
- MySQL
- Git
- A web browser

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/doradojoana508-source/SIT-EnrollEase.git
cd SIT-EnrollEase
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the Database

1. Open the XAMPP Control Panel.
2. Start Apache and MySQL.
3. Open phpMyAdmin at `http://localhost/phpmyadmin`.
4. Create a MySQL database using the database name configured in the application.
5. Select the database and import `schema.sql`.

### 5. Configure the Application

Use `config.example.py` as a reference.

Create your local configuration file:

```powershell
Copy-Item config.example.py config.py
```

Update `config.py` with your local database connection settings and other required configuration values.

**Security reminder:** Never upload actual passwords, email credentials, secret keys, or other sensitive configuration values to GitHub.

### 6. Initialize the Database

After importing `schema.sql`, run:

```bash
python seed.py
```

**Important:** Follow this database initialization order:

1. Import `schema.sql`.
2. Run `python seed.py`.

Back up existing database records before reinitializing a database.

### 7. Run the Application

Make sure MySQL is running and your virtual environment is activated.

```bash
python app.py
```

Open your browser and visit:

`http://127.0.0.1:5000/`

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
**Client Representative:** Ms. Lars Bernardo, Registrar

The project was developed based on the client's requirements and feedback regarding enrollment processes, student information management, academic records, and administrative reporting.

## Developer

**Joana Dorado**  
Bachelor of Science in Information Technology  
Laguna University

## Important Notes

- Use your own local database credentials and configuration.
- Keep sensitive information out of the public repository.
- Do not upload real student records or private application documents.
- Review database migration scripts before applying them to an existing database.
- Use appropriate security measures when deploying the application.

## Repository

[GitHub – SIT-EnrollEase](https://github.com/doradojoana508-source/SIT-EnrollEase)

## License

This project was developed as an academic project for Simons Institute of Theology.