# -*- encoding: utf-8 -*-
""" Belphegor
A simple server that provides website capture as image
Licence: GPLv3
Author: Patrice FERLET <metal3d@gmail.com>
"""
import os
import json
from ghost import Ghost
from cgi import parse_qs, escape

from PyQt4.QtCore import QBuffer, QIODevice
import logging
logging.getLogger().setLevel(logging.DEBUG)


MAXRETRIES = 5
MAXSLEEP   = 10
SLEEPSTEP = 0.01


def scroll_to_bottom(session):
    """ Scroll down page
    see https://github.com/jeanphix/Ghost.py/issues/259
    """
    x = session.main_frame.scrollPosition().x()
    y = 0
    height = session.page.viewportSize().height()
    logging.info("frame %d %d %d" % (height, x, y))

    while y + height < session.main_frame.contentsSize().height():
        y = y + height
        logging.debug("scroll %d %d" % (x, y))
        session.main_frame.scroll(x, y)
        session.sleep()

    session.wait_for_page_loaded()


def capture_image(session, selector=None, outformat="jpg"):
    """ capture page as image """

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
    return buffer, 'image/' + 'jpeg' if outformat.upper() in ('JPG','JPEG') else 'png'

    

def open_url(session, url, waitforselector=None, waittext=None, lazy=False):
    """ Open url in the given session """

    MAXTRIES = MAXRETRIES

    while MAXTRIES > 0:
        try:
            page, extra_resources = session.open(url)

            # wait for a css selector
            if waitforselector is not None:
                try:
                    session.wait_for_selector(waitforselector, timeout=90)
                except Exception, e:
                    logging.exception(e)
                    pass
            if waittext is not None:
                try:
                    session.wait_for_text(waittext, timeout=30)
                except Exception, e:
                    logging.exception(e)

        except Exception, e:
            MAXTRIES -= 1
            logging.exception("[RETRY] %s %d %s" % (url, MAXTRIES,e))
        else:
            MAXTRIES = 0 # if no exception
            logging.info("[FETCHED] %s" % url)

    if not lazy:
        scroll_to_bottom(session)


def loadpage(url, 
        outformat='JPG',
        w=1024,
        h=10,
        selector=None, 
        waitsecond=None, 
        waitforselector=None,
        waittext=None,
        recalc=False,
        agent=None):
    """ Load page and capture output """

    status = "404 NotFound"
    response_headers = []
    response_body = ["404 NotFound"]
    content_type="text/html"

    if url is None or url == "":
        return status, response_headers, response_body

    ghost = Ghost()
    try:
        # append suffix if any
        agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2%s' % (' '+agent if agent is not None else '')

        with ghost.start(java_enabled=False, display=False, user_agent=agent) as session:
            # manage proxy
            if "http_proxy" in os.environ:
                host, port = os.environ["http_proxy"].replace("http://","").split(":")
                session.set_proxy("http", host=host, port=int(port))

            # set viewport size to a minimal height
            session.set_viewport_size(w, h)
            
            # load page
            open_url(session, url, waitforselector, waittext, recalc)

            if recalc:
                # set the view port to stick to the real height before to reload
                session.set_viewport_size(w, session.main_frame.contentsSize().height())

                # if recalc is true, we can now 
                # reload page with the correct viewport size
                open_url(session, url, waitforselector, waittext)

            if waitsecond is not None:
                waitsecond = float(waitsecond) if waitsecond <= MAXSLEEP else MAXSLEEP
                while waitsecond > 0.0:
                    waitsecond -= SLEEPSTEP
                    session.sleep(SLEEPSTEP)

            if outformat.upper() in ('PNG', 'JPG', 'JPEG'):
                buffer, content_type = capture_image(session, outformat=outformat, selector=selector)
                buffer = buffer.data()
            else:
                buffer = session.content.encode("utf-8")
            
        # write image
        response_body = [bytes(buffer)]
        status = "200 OK"
        response_headers = [
            ('Content-Type', content_type),
        ]

    except Exception, e:
        logging.exception(e)
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
    """ Returns the get/post param or a default value"""

    ret = qs.get(name, [value])
    # probably taken from json, it's a string, int, float...
    if type(ret) is not list:
        return ret

    # so... it's a list
    return ret[0]


def check_add_cors(response_headers, environ):
    # If we allow origin to be callable from ajax:
    CORS = os.environ.get('CORS', False)
    if CORS:
        if CORS in ("true", True): CORS = "*"
        response_headers.append(('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'))
        response_headers.append(('Access-Control-Allow-Origin', CORS))
        ach = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', False)
        if ach: response_headers.append(('Access-Control-Allow-Headers', ach))
        return True
    return False


def app(environ, start_response):
    """ Main WSGI application """

    agent = None
    if 'USER_AGENT_SUFFIX' in os.environ:
        agent = os.environ['USER_AGENT_SUFFIX']

    d = parse_qs(environ['QUERY_STRING'])


    if environ.get('REQUEST_METHOD') == 'OPTIONS':
        response_headers = []
        check_add_cors(response_headers, environ)
        start_response('201 NoContent', response_headers)
        return ''

    if environ.get('REQUEST_METHOD', 'GET') == 'POST':
        request_body_size = 0
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            pass

        request_body = environ['wsgi.input'].read(request_body_size)

        # try to load json
        if environ.get('CONTENT_TYPE', '') == 'application/json':
            try:
                post_data = json.loads(request_body)
                d.update(post_data)
            except Exception, e:
                logging.exception(e)
                start_response('400 BadRequest',[
                    ('Content-Type', 'application/json')
                ])
                return '{"error": "%s"}' % str(e)
        else:
            d.update(parse_qs(request_body))

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
    viewportheight  = int(get_param(d, 'viewportheight', 550))
    # output catpure format (png, jpeg, jpg, html)
    outformat       = get_param(d, 'output', 'jpeg')
    # if the content is lazy loaded, that will reload page with a calculated
    # page height: so there will be 2 page load !
    recalc          = get_param(d, 'lazy', 'false')
    # force to wait before to do the capture
    waitsecond      = get_param(d, 'sleep', None)
    # suffix user-agent
    agent           = get_param(d, "uasuffix", agent)

    status, response_headers, response_body = loadpage(
            url, 
            outformat, 
            viewportwidth, 
            viewportheight,
            selector, 
            waitsecond,
            waitforselector, 
            waittext, 
            recalc=recalc.lower() == 'true',
            agent = agent
        )
            
    check_add_cors(response_headers, environ)

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
