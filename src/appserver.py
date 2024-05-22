# https://www.piware.de/2011/01/creating-an-https-server-in-python/
#
# invoke with py devserver.py path_to_mainpage

from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import ssl, json, threading, webbrowser, time, sys, os, stat, datetime, shutil, subprocess, re, stat
import tkinter as tk
import tkinter.filedialog as fd

rootdir = os.getcwd()


def abspath(path):
    """
    works out the absolute path.
    Parameters:
        path - a string path. if path is relative, return the
            absolute path based on the rootdir

    Returns:
       the absolute path.
    """
    return os.path.normpath(os.path.join(rootdir, path))


# The router:

routes = {}


def route(f):
    """
    a routing decorator. It wraps the route function in an arror
    handling function and stores it in the route.

    Parameters:
        f - the function to call. The name of the functions defines the route.
            e.g. if the functon is a_b_c, the route is '/a/b/c'

    The function being decorated *must* take (handler, *args) parameters.
    """

    def trycatch(f, handler, *args):
        # wraps f in a try-catch statement. If an exception
        # occurs, the exception is passed back to the webpage as a 404 error
        try:
            f(handler, *args)
        except Exception as e:
            handler.respond(404, "text/plain", str(e))
            raise e

    routename = "/" + f.__name__.replace("_", "/")
    routes[routename] = lambda handler, *args: trycatch(f, handler, *args)
    return f


# some routes:


@route
def api_fs_readtext(handler, path, content_type="text/plain"):
    """
    read a text file

    Parameters:
        path - the path to the file
        content_type - the response content type

    Response:
        returns the text file contents.
    """
    with open(abspath(path), "rb") as f:  # open as bytes to avoid encoding
        contents = f.read()  # as text/plain
    handler.respond(200, content_type, contents)


@route
def api_fs_readbinary(handler, path, content_type="application/octet-stream"):
    """
    read a binary file

    Parameters:
        path - the path to the file

    Response:
        returns the file contents as an octet-stream.

    There's not much difference between this and the readtext function.
    """
    with open(abspath(path), "rb") as f:
        contents = f.read()
    handler.respond(200, content_type, contents)


@route
def api_fs_readfolder(handler, path):
    """
    read contents of a folder

    Parameters:
        path - the path to the directory
    """
    dirlist = []
    dirpath = abspath(path)
    for f in os.listdir(dirpath):
        fpath = os.path.join(dirpath, f)
        if os.path.isfile(fpath):
            dirlist.append({"name": f, "path": fpath, "type": "file"})
        elif os.path.isdir(fpath):
            dirlist.append({"name": f, "path": fpath, "type": "folder"})
        else:
            dirlist.append({"name": f, "path": fpath, "type": "other"})
    handler.respond(200, "application/json", json.dumps(dirlist))


def todatestr(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S.%f%z")


@route
def api_fs_getstats(handler, path):
    """
    get file stats

    Parameters:
        path - the path to the file

    Response:
        returns a json object {path, type, accessed, modified, created}.
    """
    path = abspath(path)
    statinfo = os.stat(path)
    statdict = {}
    statdict["path"] = path
    statdict["type"] = "folder" if stat.S_ISDIR(statinfo.st_mode) else "file"
    statdict["accessed"] = todatestr(statinfo.st_atime)
    statdict["modified"] = todatestr(statinfo.st_mtime)
    try:
        statdict["created"] = statinfo.st_birthtime
    except:
        statdict["created"] = statinfo.st_ctime
    statdict["created"] = todatestr(statdict["created"])
    handler.respond(200, "application/json", json.dumps(statdict))


@route
def api_fs_deletefile(handler, paths):
    """
    delete one or more files

    Parameters:
        paths - array of paths to delete.

    Returns:
        array of true/false whether the delete succeeded or not.
    """
    result = []
    for p in paths:
        try:
            os.remove(p)
            result.append(True)
        except:
            result.append(False)
    handler.respond(200, "application/json", json.dumps(result))


@route
def api_fs_makefolder(handler, args):
    """
    creates a folder

    Parameters:
        args - a dict {path, exist_ok} which lets you create a folder, including any
            intermediate elements. exist_ok=false will raise an error if the directory exists
    """
    os.makedirs(args["path"], exist_ok=args["exist_ok"])
    handler.respond(200)


@route
def api_fs_deletefolder(handler, path):
    """
    removes a folder

    Parameters:
        path - the path to the folder to remove. The folder must be empty
    """
    os.chmod(path, stat.S_IWUSR) # windows likes to make it hard to remove folders
    os.rmdir(path)
    handler.respond(200)


@route
def api_fs_writefile(handler, args):
    """
    write a file

    Parameters:
        args - an object {path, contents} describing the file to write

    """
    args["path"] = args["path"].decode("utf-8")
    with open(abspath(args["path"]), "wb") as f:
        f.write(args["contents"])
    # and respond
    handler.respond(200)


@route
def api_fs_copyfile(handler, args):
    if type(args) not in (list, tuple):
        args = (args,)
    for a in args:
        shutil.copy(a["src"], a["dest"])
    handler.respond(200)


@route
def api_fs_relativepath(handler, path):
    # path relative to the rootdir.
    handler.respond(200, "text/plain", os.path.relpath(path, rootdir))


class TKRoot:
    def __init__(self):
        self.root = None

    def __enter__(self):
        self.root = tk.Tk()
        self.root.attributes("-alpha", 0.0)
        self.root.lift()
        return self.root

    def __exit__(self, exc_type, exc_value, traceback):
        self.root.destroy()


@route
def api_ui_chooseopenfile(handler, args):
    # args are title, initialdir, initialfile, filetypes [(label, pattern), (label, patterns), ...],
    # defaultextension
    with TKRoot() as root:
        fname = fd.askopenfilename(parent=root, **args)
        handler.respond(200, "text/plain", fname)


@route
def api_ui_choosesavefile(handler, args):
    with TKRoot() as root:
        fname = fd.asksaveasfilename(parent=None, **args)
        handler.respond(200, "text/plain", fname)


@route
def api_ui_choosefolder(handler, args):
    with TKRoot() as root:
        fname = fd.askdirectory(parent=None, **args)
        handler.respond(200, "text/plain", fname)


_quit_server = False


@route
def api_exit(handler):
    handler.respond(204)
    global _quit_server
    _quit_server = True


@route
def api_command(handler, cmd):
    # cmd could be a string or array of strings
    subprocess.Popen(cmd)
    handler.respond(200, "text/plain", "done")


class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        urlobj = urlparse(self.path)
        print(urlobj.path)
        if urlobj.path.startswith("/api/"):
            # handle errors here
            if urlobj.query == "":
                routes[urlobj.path](self)  # dummy args to keep calling simple
            else:
                query = parse_qs(urlobj.query)
                args = json.loads(query["args"][0])
                routes[urlobj.path](self, args)
        else:
            # this is fine unless you want cache control
            # and maybe absolute paths.
            if self.path == "/@api.js":
                apipath = os.path.join(os.path.dirname(__file__), "api.js")
                routes["/api/fs/readtext"](self, apipath, "application/json")
            else:
                # convert to a relative path from rootdir & then get it
                super().do_GET()

    def do_PUT(self):
        urlobj = urlparse(self.path)
        if urlobj.path.startswith("/api/"):
            # do different depending on content type
            request_headers = self.headers
            content_length = request_headers["Content-Length"]
            length = int(content_length) if content_length else 0
            content = self.rfile.read(length)
            if request_headers["Content-Type"] == "multipart/form-data":
                data = self.decode_multipart(content)
            elif request_headers["Content-Type"] == "application/json":
                print(content)
                data = json.loads(content.decode("utf-8"))
            routes[urlobj.path](self, data)

    def respond(self, code, content_type=None, contents_b=None):
        # does the response
        self.send_response(code)
        if content_type:
            self.send_header("Content-type", content_type)
        # to stop cacheing, use no-store for extra privacy
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if contents_b:
            if type(contents_b) != bytes:
                contents_b = contents_b.encode("utf-8")
            else:
                print("bytes object", content_type)
            self.wfile.write(contents_b)

    def decode_multipart(self, mp):
        # decodes the multipart bytes
        # very basic, doesn't work with filename= fields.
        seplen = mp.find(b"\r\n") + 2  # the length of the separator string + '\r\n'
        mp = mp.split(mp[:seplen])[
            1:
        ]  # split by separator, and drop the '' at the start
        # the last of the parts has the end which is -- added
        mp[-1] = mp[-1][: -(seplen + 2)]
        # split each part into name & contents
        data = {}
        for part in mp:
            meta, content = part[:-2].split(b"\r\n\r\n", maxsplit=1)
            if meta.startswith(b"Content-Disposition: form-data;"):
                key = re.search(b'name="([^"]*)"', meta)[1].decode("utf-8")
                print(key, len(content))
                data[key] = content
            else:
                pass  # no other dispositions are used.
        return data


if __name__ == "__main__":

    address = ("localhost", 4443)

    # get start directory/page
    rootdir = os.getcwd()
    entryfile = ""
    if len(sys.argv) > 1:
        rootdir, entryfile = os.path.split(abspath(sys.argv[1]))
        os.chdir(rootdir)
    entryfile = entryfile or "index.html"
    rootdir = os.getcwd()  # just for formatting reasons

    # need to work if pem files are not available and do a different context
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=os.path.join(os.path.dirname(__file__), "localhost.pem"),
            keyfile=os.path.join(os.path.dirname(__file__), "localhost-key.pem"),
        )
        context.check_hostname = False
        protocol = "https"
    except:
        context = None
        protocol = "http"

    def start_server():
        with HTTPServer(address, MyHandler) as httpd:
            if context:
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            httpd.serve_forever()

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    webbrowser.open_new(f"{protocol}://{address[0]}:{address[1]}/{entryfile}")

    while True:
        try:
            time.sleep(1)
            if _quit_server:
                sys.exit(0)
        except:
            sys.exit(0)
