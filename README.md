# COVID-19 Disaster Consult Website


## Prerequisites

- Python 3.6
- pip ( For python 3.6)



## Links

[AWS Master Website](https://www.disasterconsult.org/)

[AWS Dev Website](http://covid19disasterconsult-dev.us-east-2.elasticbeanstalk.com/)


Local server is run at:

```
http://127.0.0.1:5000
```

Admin panel:

```
<site address>/admin
```


## Starting Server

1. Open folder in terminal

2. Open virtual environment

```
Windows: venv\Scripts\activate.bat
```

```
MacOS: source venv/bin/activate
```


3. Start Server

```
python application.py
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
python application.py
```

9. Server can be accessed at:

```
http://127.0.0.1:5000
```
