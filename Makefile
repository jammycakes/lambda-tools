.PHONY: test build release upload upload-test

VERSION = $(shell python3 -c "import lambda_tools;print(lambda_tools.VERSION)")

test:
	python3 setup.py test -a tests

build:
	python3 setup.py sdist

release:
	git tag $(VERSION) -m "Tag version $(VERSION)"
	git push --tags origin master

upload: build
	pip install twine
	twine upload dist/* --skip-existing

upload-test: build
	pip install twine
	twine upload dist/* --repository-url https://test.pypi.org/legacy/ --skip-existing