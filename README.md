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
git clone https://github.com/metal3d/docker-belphegor.git
cd docker-belphegor
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
- waitforselector: a CSS selector to wait before to make the capture
- selector: only capture this selector
- resolution: WxH where W and H are Width and Height in pixel. This set the viewport (default is 1024x768)

Note that height is adapted if the page is higher.

