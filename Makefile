.PHONY: test build tag upload upload-test

VERSION = $(shell cat .version)

test:
	python3 setup.py test -a tests

build:
	python3 setup.py sdist

tag:
	git tag $(VERSION) -m "Tag version $(VERSION)"
	git push --tags origin master

upload: build
	python setup.py sdist upload

upload-test: build
	python setup.py sdist upload -r pypitest