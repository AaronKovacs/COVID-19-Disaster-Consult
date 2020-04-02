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

4. Install python virtual-env

```
pip install virtualenv
```

5. Create a virtual python environment to install dependencies in

```
virtualenv -p python3 venv
```

6. Open virtual environment

```
source venv/bin/activate
```

7. Install the dependencies

```
pip install -r requirements.txt
```

8. Run the server

```
FLASK_APP=application.py FLASK_ENV=development flask run --host=0.0.0.0
```

9. Server can be accessed at:

```
http://127.0.0.1:5000
```
