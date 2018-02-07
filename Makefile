.PHONY: test build deps release upload upload-test

VERSION = $(shell python -c "import lambda_tools;print(lambda_tools.VERSION)")

test:
	python setup.py test -a tests

build:
	python setup.py sdist

deps:
	pip install -U -r requirements.txt

release:
	git tag $(VERSION) -m "Tag version $(VERSION)"
	git push --tags origin master

upload: build
	pip install twine
	twine upload dist/* --skip-existing

upload-test: build
	pip install twine
	twine upload dist/* --repository-url https://test.pypi.org/legacy/ --skip-existing
