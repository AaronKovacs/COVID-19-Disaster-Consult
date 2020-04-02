## Prerequisites

- Python 3.6
- pip ( For python 3.6)

## Starting Server

1. Open folder in terminal

2. Open virtual environment

```
source venv/bin/activate
```

3. Start Server

```
FLASK_APP=application.py FLASK_ENV=development flask run --host=0.0.0.0
```


## First Time Setup

1. First clone the repositiory to where you'd like to work.

```
git clone https://github.com/AaronKovacs/COVID-19-Disaster-Consult.git
```


2. Open the Folder in Terminal

```
cd COVID-19-Disaster-Consult
```


3. Copy provided /secrets folder to /source

5. Install python virtual-env

```
pip install virtualenv
```

4. Create a virtual python environment to install dependencies in

```
virtualenv -p python3 venv
```

5. Install the dependencies

```
pip install -r requirements.txt
```

6. Run the server

```
FLASK_APP=application.py FLASK_ENV=development flask run --host=0.0.0.0
```

7. Server can be accessed at:

```
http://127.0.0.1:5000
```