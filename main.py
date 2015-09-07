# -*- encoding: utf-8 -*-
""" Belphegor
A simple server that provides website capture as image
Licence: GPLv3
Author: Patrice FERLET <metal3d@gmail.com>
"""
import os
import time
from ghost import Ghost
from cgi import parse_qs, escape

from PyQt4.QtCore import QBuffer, QIODevice


MAXRETRIES = 5
MAXSLEEP   = 10

def open_url(session, url, waitforselector=None, waittext=None):
    """ Open url in the given session """

    MAXTRIES = MAXRETRIES

    while MAXTRIES > 0:
        try:
            page, extra_resources = session.open(url)

            # wait for a css selector
            if waitforselector is not None:
                try:
                    session.wait_for_selector(waitforselector, timeout=90)
                except:
                    pass
            if waittext is not None:
                try:
                    session.wait_for_text(waittext, timeout=30)
                except:
                    pass

        except Exception, e:
            MAXTRIES -= 1
            print "[RETRY]", url, MAXTRIES, ':: CAUSE: ', e
        else:
            MAXTRIES = 0 # if no exception
            print "[FETCHED]", url


def loadpage(url, 
        outformat='JPG',
        w=1024,
        h=10,
        selector=None, 
        waitsecond=None, 
        waitforselector=None,
        waittext=None,
        recalc=False):
    """ Load page and capture output """

    status = "404 NotFound"
    response_headers = []
    response_body = ["404 NotFound"]
    if url is None or url == "":
        return status, response_headers, response_body

    ghost = Ghost()
    try:
        with ghost.start(java_enabled=False) as session:
            # manage proxy
            if "http_proxy" in os.environ:
                host, port = os.environ["http_proxy"].replace("http://","").split(":")
                session.set_proxy("http", host=host, port=int(port))

            # set viewport size to a minimal height
            session.set_viewport_size(w, h)
            
            # load page
            open_url(session, url, waitforselector, waittext)

            if recalc:
                # set the view port to stick to the real height before to reload
                session.set_viewport_size(w, session.main_frame.contentsSize().height())

                # if recalc is true, we can now 
                # reload page with the correct viewport size
                open_url(session, url, waitforselector, waittext)

            if waitsecond is not None:
                waitsecond = int(waitsecond) if waitsecond <= MAXSLEEP else MAXSLEEP
                #session.sleep(waitsecond)
                time.sleep(waitsecond)

            # do capture now
            cap = None
            if selector is not None:
                cap = session.capture(selector=selector)
            else:
                cap = session.capture()

            # create a buffered image
            buffer = QBuffer()
            buffer.open(QIODevice.ReadWrite)
            cap.save(buffer, 'JPG' if outformat.upper() in ('JPG', 'JPEG') else 'PNG')
            buffer.close()

        # write image
        response_body = [bytes(buffer.data())]
        status = "200 OK"
        response_headers = [
            ('Content-Type', 'image/' + 'jpeg' 
                if outformat.upper() in ('JPG','JPEG') else 'PNG'),
        ]
    except Exception, e:
        print e
        response_body = [
            "There were an error...",
            "\n",
            str(e)
        ]
        status = "500 InternalServerError"
        response_headers = [
            ('Content-Type', 'text/plain'),
        ]

    return status, response_headers, response_body



def get_param(qs, name, value):
    return qs.get(name, [value])[0]

def app(environ, start_response):
    """ Main WSGI application """

    d = parse_qs(environ['QUERY_STRING'])

    # url to load
    url             = get_param(d, 'url', None)
    # selector to capture (css)
    selector        = get_param(d, 'selector', None) 
    # wait that selector before to catpure
    waitforselector = get_param(d, 'waitforselector', None)
    # wait that text before to capture
    waittext        = get_param(d, 'waittext', None)
    # width of virtual browser
    viewportwidth   = int(get_param(d, 'viewportwidth', 1024))
    # height of virtual browser
    viewportheight   = int(get_param(d, 'viewportheight', 10))
    # output catpure format (png, jpeg)
    outformat       = get_param(d, 'output', 'jpeg')
    # if the content is lazy loaded, that will reload page with a calculated
    # page height: so there will be 2 page load !
    recalc          = get_param(d, 'lazy', 'false')
    # force to wait before to do the capture
    waitsecond      = get_param(d, 'sleep', None)

    status, response_headers, response_body = loadpage(
            url, 
            outformat, 
            viewportwidth, 
            viewportheight,
            selector, 
            waitsecond,
            waitforselector, 
            waittext, 
            recalc=recalc.lower() == 'true'
        )
            
    # start to respond
    start_response(status, response_headers)
    return response_body
    
if __name__ == "__main__":
    # a simple server if this script is called directly by python
    # => it's recommanded to use it for test only, please use
    # gunicorn instead (with `gunicorn main:app`)
    from wsgiref.simple_server import make_server
    httpd = make_server(
        '0.0.0.0',
        8000,
        app
    )
    httpd.serve_forever()
