# https://www.piware.de/2011/01/creating-an-https-server-in-python/
#
# invoke with py server.py path_to_mainpage
# if no path given, the server attempts to open index.html in the current dir
# and if that fails, opens a directory list

from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl, threading, webbrowser, time, sys, os

if __name__ == "__main__":

    address = ("localhost", 4443)

    # get start directory/page from command line
    rootdir = os.getcwd()
    entryfile = ""
    if len(sys.argv) > 1:
        rootdir, entryfile = os.path.split(
            os.path.normpath(os.path.join(rootdir, sys.argv[1]))
        )
        os.chdir(rootdir)
        rootdir = os.getcwd()  # for formatting reasons

    try:
        # run https if pem files are found
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=os.path.join(os.path.dirname(__file__), "localhost.pem"),
            keyfile=os.path.join(os.path.dirname(__file__), "localhost-key.pem"),
        )
        context.check_hostname = False
        protocol = "https"
    except:
        # run http
        context = None
        protocol = "http"

    def start_server():
        # the server runs in a daemon thread
        with HTTPServer(address, SimpleHTTPRequestHandler) as httpd:
            if context:
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            httpd.serve_forever()

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # pop open the web browser
    webbrowser.open_new(f"{protocol}://{address[0]}:{address[1]}/{entryfile}")

    # go into a loop

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)
