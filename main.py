import os
import time
from ghost import Ghost
from cgi import parse_qs, escape

from PyQt4.QtCore import QBuffer, QIODevice


def open_url(session, url, waitforselector=None, waittext=None):
    """ Open url in the given session """

    MAXTRIES = 5

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

            session.wait_for_page_loaded()
        except Exception, e:
            MAXTRIES -= 1
            print "retry", MAXTRIES, e
        else:
            MAXTRIES = 0 # if no exception
            print "done !"


def loadpage(url, outformat='JPG', w=1024, selector=None, waitforselector=None, waittext=None, recalc=False):
    """ Load page and capture output """

    status = "404 NotFound"
    response_headers = []
    response_body = ["404 NotFound"]
    if url == "":
        return status, response_headers, response_body

    ghost = Ghost()
    try:
        with ghost.start(java_enabled=False) as session:
            # manage proxy
            if "http_proxy" in os.environ:
                host, port = os.environ["http_proxy"].replace("http://","").split(":")
                session.set_proxy("http", host=host, port=int(port))

            # set viewport size
            session.set_viewport_size(w,768) # base height = 768
            
            # load page
            open_url(session, url, waitforselector, waittext)
            session.wait_for_page_loaded()

            # set the view port to stick to the real height
            session.set_viewport_size(w, session.main_frame.contentsSize().height())

            if recalc:
                # if recalc is true, we can now 
                # reload page with the correct viewport size
                open_url(session, url, waitforselector, waittext)
                session.wait_for_page_loaded()

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
            ('Content-Type', 'image/' + 'jpeg' if outformat.upper() in ('JPG','JPEG') else 'PNG'),
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
    # output catpure format (png, jpeg)
    outformat       = get_param(d, 'output', 'jpeg')
    # if the content is lazy loaded, that will reload page with a calculated
    # page height: so there will be 2 page load !
    recalc          = get_param(d, 'lazy', 'false')

    status, response_headers, response_body = loadpage(
            url, 
            outformat, 
            viewportwidth, 
            selector, 
            waitforselector, 
            waittext, 
            recalc=True if recalc.lower() == 'true' else False
        )
            
    start_response(status, response_headers)
    return iter(response_body)
    
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    httpd = make_server(
        '0.0.0.0',
        8000,
        app
    )
    httpd.serve_forever()
