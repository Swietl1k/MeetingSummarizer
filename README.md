# Instructions to Set Up the Backend

## Prerequisites
1. **Python**: Ensure you have Python 3.8 or higher installed. You can download it from [python.org](https://www.python.org/downloads/).
2. **Pip**: Ensure you have pip installed. Pip is the package installer for Python. It is usually included with Python installations.
3. **Virtual Environment**: It is recommended to use a virtual environment to manage dependencies. You can create one using `python -m venv env`.

## Steps to Set Up the Backend

1. **Clone the Repository**:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```

2. **Create and activate a Virtual Environment**

3. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

4. **Set up the database**:
    In this project we used a Postgres database hosted on railway.app.
    Log into railway and deploy a postgres database with free trial tokens.
    In the 'Variables' tab you can find the host name, port and password .
    In settings.py change the variables in DATABASES={} accordingly and set the railway key (next step).
    
5. **Set Up Environment Variables**:
    Create a .env file in the parent directory of the project's root and add the following environment variables:
    ```
    DJANGO_SECRET_KEY=<your_django_key>
    RAILWAY_IO_PASSWORD=<password_to_railway>
    GROQ_API_KEY=<your_groq_api_key>
    ```

6. **Install Tesseract**:
    Ensure that the Tesseract executable is in your system's PATH.

7. **Link Tesseract Executable in `tasks/processing.py`**:
    In your tasks/processing.py, ensure that the path to the Tesseract executable is correctly set. For example:
    ```python
    TESSERACT_PATH = 'C:\\Program Files\\Tesseract-OCR\\tesseract'
    ```

8. **Set frontend's origin**:
    In settings.py update CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS with your frontend's adress.

10. **Run Migrations**:
    ```sh
    python manage.py migrate
    ```

11. **Start the Development Server**:
    ```sh
    python manage.py runserver
    ```

By following these steps, you should be able to set up and run the backend successfully.


# Instructions to Set Up the Frontend

## Steps to Set Up the Frontend

1. **Install extension to VS Code - "Live Server"**

2. **In VS Code open file frontend/login-register.html**

3. **Click the "Go Live" button located on the right side of the VS Code's bottom bar**

After completing the above steps, your frontend should be accessible on following url: http://127.0.0.1:5500/frontend/views/login-register.html.