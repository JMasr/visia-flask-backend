# visia-flask-backend
Repository of the Visia's Backend using Flask+MongoDB

### Requirements

* A MongoDB instance running on the default port (27017) 
* Python 3.10 or higher


### Installation
1. Clone the repository

2. Install the requirements:
    ```bash
    pip install -r requirements.txt
    ```
3. Copy the extras to your environment

4. Run the application:
    ``` bash
    SET FLASK_APP=app.py
    SET FLASK_ENV=development
    python -m flask run
    ```

### Usage

### Bugs
* Problem related with the flask_mongoengine -> json.py
https://github.com/MongoEngine/flask-mongoengine/blob/master/flask_mongoengine/json.py

* Problem related with the flask_uploads module
https://stackoverflow.com/questions/61628503/flask-uploads-importerror-cannot-import-name-secure-filename

* Problem related with the flask_cors module
https://answers.microsoft.com/en-us/microsoftedge/forum/all/disable-cors/55c89fb6-8d72-4318-9ee3-e9cdfc6fa708