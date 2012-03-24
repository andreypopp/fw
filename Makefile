install test clean:
	python setup.py $@

develop:
	pip install -r requirements.txt
	python setup.py develop

reqs:
	pip install --upgrade -r requirements.txt

serve:
	python ./fw.py
