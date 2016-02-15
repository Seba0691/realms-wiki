# Realms Wiki Beta

Git based wiki written in Python
Inspired by [Gollum][gollum], [Ghost][ghost], and [Dillinger][dillinger].
Basic authentication and registration included.

**Forked from the project of [Matthew Scragg (scragg0x)](https://github.com/scragg0x/realms-wiki)**

## Improvements

- Added a standard homepage
- Added an auto-generated sidebar in order to provide a Table Of Content for the wiki
- Added the possibiliy to have multiple wikis in the same repository, each of them with its Table Of Content
```
+- root/
    |
    +- wiki1/
    .    |
    .    +- wiki1_page_1.md
    .    .
    .    .
    .    +- wiki1_page_n.md
    .
    .
    +- wikin/
         |
         +- wikin_page_1.md
         .
         .
         +- wikin_page_n.md
```
- AJAX image upload in the creation / edit of a page (WORK IN PROGRESS)
- Creation of a new page in the current sub directory as default


## Developing

It is mandatory to have [Docker](https://www.docker.com/) in order to deploy this application.

1. install the dependencies with bower
```
bower install
```
2. Build the image from the Dockerfile_dev
```
mkdir $HOME/Dockerfile_realms_dev

mv ./docker/Dockerfile_dev  $HOME/Dockerfile_realms_dev/Dockerfile

cd $HOME/Dockerfile_realms_dev/

docker build -t realms-dev .
```
3. Run the created image and mount this repository as root of the application (OPT : mount a host directory in order to make the created page in the wiki persistent)
```
docker run --name realms-wiki -p 5000:5000 -t -i -v <PATH_TO_THIS_REPO>/realms:/home/deploy/realms-wiki/.venv/lib/python2.7/site-packages/realms -v <PATH_TO_SAMPLE_WIKI>:/tmp/wiki --rm realms-dev
```


