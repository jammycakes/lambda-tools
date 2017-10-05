.PHONY: build upload

VERSION = $(shell cat .version)

build:
	python3 setup.py sdist

tag:
	git tag $(VERSION) -m "Tag version $(VERSION)"
	git push --tags origin master

upload: build
	python setup.py upload

upload-test: build
	python setup.py upload -r pypitest