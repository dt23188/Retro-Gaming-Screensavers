.PHONY: test
test:
	python3 -m unittest discover -s tests -v
	PYTHONPATH=snake/src python3 -m unittest discover -s snake/tests -p test_portable.py -v
