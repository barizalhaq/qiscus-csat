# Qismo CSAT
Qismo Customer Satisfaction for Multiple AppID. Quip documentation: https://quip.com/G5L7AacA6tZD/Qismo-CSAT-for-Multiple-AppID

### Requirements

- Python3
- Docker Use [Docker CE](https://docs.docker.com/engine/installation) for Linux or [Docker Toolbox](https://www.docker.com/products/docker-toolbox) for Windows and Mac.


### Setting up Project

Create virtual environment
```bash
python3 -m venv venv
```
Activate virtual environment
```bash
source venv/bin/activate
```
Install all project dependencies.
```bash
pip install -r requirements.txt
```
Setup environtment variable. Rename `.env.example` to `.env`.


### How to Run

Service requires PostgreSQL, run PostgreSQL on your local machine or run it using docker with the following command
```bash
docker run --name qismocsat -d -p 5432:5432 -e POSTGRES_USER=qismocsat -e POSTGRES_PASSWORD=qismocsat-123 -e POSTGRES_DB=qismocsat postgres
```
Run server
```bash
# debug mode: off
flask run

# debug mode: on
python3 run.py
```

### Other

Flask commands
```bash
routes  Show the routes for the app.
run     Run a development server.
shell   Run a shell in the app context.
```