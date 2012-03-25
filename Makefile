all: serve

install test clean:
	python setup.py $@

develop:
	pip install -r requirements.txt
	python setup.py develop

reqs:
	pip install --upgrade -r requirements.txt

serve:
	python ./fw.py

_recreate:
	./psql -c "drop schema if exists fw cascade;"
	./psql < friendwave.sql
