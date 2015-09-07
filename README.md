# Belphegor

Webserver that creates website capture image.

Belphegor makes use of [Ghost.py](https://github.com/jeanphix/Ghost.py) to create screen captures of webpages. 

To use is in a docker container, please check [docker-belphegor](http://github.com/metal3d/docker-belphegor).

# Installation

You'll need PySide or PyQt4, note that PySide is no longer maintained. It's recommanded to use your package distribution to install PyQt4

```
# Debian, Ubuntu
apt-get install python-qt4

# Fedora, CentOS
dnf install python-qt4

```

Then install Ghost.py

```
pip install Ghost.py
```

Get this repository:

```
git clone https://github.com/metal3d/belphegor.git
cd belphegor
```


Just launch 


```
python main.py

# or use gunicorn (installed with `pip install gunicorn`)

gunicorn main:app -b :8000 -w 4 

```

# Params

You may use GET params:

- url: mandatory, the url to capture
- selector: only capture this selector
- waitforselector: a CSS selector to wait before to realize the capture
- waitfortext: wait for that text on the page to realize the capture
- viewportwidth: with of the virtual browser
- output: format for output, png or jpg (any other given format will result of a png)
- lazy: if there are lazy loaded content (images when scroll down for example), this option set to "true" will load page twice (one time to get the real height, and another time to get images)

