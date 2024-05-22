/** javascript functions to communicate with the server.
 *  Use these by including a script tag
 *  <script src='@api.js'></script>
 *
 * The '@' character makes the server look for this file in the same place as the appserver.py file.
 */

var api = (() => {
    let origin = window.location.origin

    async function get(route, args, rtype) {
        /** GET
         *
         * @param route - string that follows '/api' e.g. '/fs/readfile' to identify the python function
         * @param args - a json object containing the arguments to the function
         * @param rtype - the return type of the response, undefined, 'json', 'text', 'blob', etc.
         *            If undefined, no response is expected or returned.
         *
         * @returns an awaitable text/json/blob response
         */
        let response
        if (args) {
            // the args get put in the query of the fetch URL
            let qs = encodeURIComponent(JSON.stringify(args))
            response = await fetch(`${origin}/api${route}?args=${qs}`)
        } else {
            // no args -> no query
            response = await fetch(`${origin}/api${route}`)
        }
        if (response.ok) {
            // return the response type (if any)
            return rtype && (await response[rtype]())
        } else {
            // there is a problem - usually a python exception
            throw await response.text()
        }
    }

    async function put(route, args, ctype, rtype) {
        /** PUT
         *
         * @param route - string that follows '/api' e.g. '/fs/readfile' to identify the python function
         * @param args - an object containing the arguments to the function
         * @param ctype - the content type of args, 'multipart/form-data', 'application/json', etc.
         * @param rtype - the return type of the response, 'json', 'text', 'blob', etc.
         *
         * @returns an awaitable text/json/blob response
         */
        let response, body
        if (ctype == 'multipart/form-data') {
            // convert args into a FormData object
            body = new FormData()
            for (let k in args) {
                body.append(k, args[k])
            }
        } else if (ctype == 'application/json') {
            // convert args to a json string
            body = JSON.stringify(args)
        }
        response = await fetch(`${origin}/api${route}`, {
            method: 'PUT',
            headers: {
                'Content-Type': ctype,
            },
            body,
        })
        if (response.ok) {
            // return the response type (if any)
            return rtype && (await response[rtype]())
        } else {
            // there is a problem - usually a python exception
            throw await response.text()
        }
    }

    async function readtext(path) {
        /** read a text file
         *
         * @param path - (string) the path to the file. This can be absolute or
         *        relative to the directory containing the main page
         *
         * @returns the awaitable contents of the file as a string.
         */
        return get('/fs/readtext', path, 'text')
    }

    async function readbinary(path) {
        /** read a text file
         *
         * @param args - the path to the file. This can be absolute or relative to the
         *          directory containing the main page
         *
         * @returns the awaitable contents of the file as a blob.
         */
        return get('/fs/readbinary', path, 'blob')
    }

    async function readfolder(path) {
        /** read the contents of a folder
         *
         * @param args - the path to the folder.
         *     The path can be absolute or relative to the directory containing the main page.
         *
         * @returns awaitable array of folder items, each of which is an object {name, path, type}
         *     name is the filename
         *     path is the absolute file path
         *     type is 'file', 'folder', or 'other'
         */
        return get('/fs/readfolder', path, 'json')
    }

    async function getstats(path) {
        /** get file stats
         *
         * @param path  - the path to the file. The path can be absolute or relative to the directory
         *    containing the main page
         *
         * @returns awaitable file stat object {path, type, accessed, modified, created}
         *    path is the absolute path to the file
         *    type is 'file', 'folder', or 'other'
         *    accessed, modified, and created are all isotime strings
         */
        return get('/fs/getstats', path, 'json')
    }

    async function writefile(path, contents) {
        /** write a text or binary filefile
         *
         * @param path  - the path to the file. The path can be absolute or relative
         *          to the directory containing the main page.
         * @param contents - the file contents, text or binary
         *
         */
        // if contents is not a string or blob, it must be converted to a blob
        // using "application/octet-stream" as the content type.
        // or application/json if it's an object?
        if (typeof contents !== 'string' && !(contents instanceof Blob)) {
            // convert it to a blob.
            console.log('convert to blob')
            contents = new Blob([contents], { type: 'application/octet-stream' })
        }
        return put('/fs/writefile', { path, contents }, 'multipart/form-data')
    }

    async function deletefile(...paths) {
        /** delete a file or files
         *
         * @param ...paths - the path(s) to the file(s). The paths can be absolute or relative to the directory
         *    containing the main page
         *
         * @returns awaitable (nothing)
         */
        return put('/fs/deletefile', paths, 'application/json', 'json')
    }

    async function makefolder(path, exist_ok = false) {
        /** create a folder
         *
         * @param path - the path to the folder.The path can be absolute or relative to the directory
         *          containing the main page.
         * @param exist_ok (optional) is a flag saying whether the create succeeds even if the folder
         *     exists
         *
         * @returns awaitable (nothing)
         */
        return put('/fs/makefolder', { path, exist_ok }, 'application/json')
    }

    async function deletefolder(path) {
        /** delete a folder and contents
         *
         * @param args - an object {path} where path is the path to the folder.
         *     The path can be absolute or relative to the directory containing the main page.
         *
         * @returns awaitable (nothing)
         */
        return put('/fs/deletefolder', path, 'application/json')
    }

    async function copyfile(...args) {
        /** copy a file or files
         *
         * @param args - an object {src,dest} where src, dest are paths to the source &
         *    destination files, or an array of such objects.
         *    The paths can be absolute or relative to the directory
         *    containing the main page
         *
         * @returns awaitable (nothing)
         */
        return put('/fs/copyfile', args, 'application/json')
    }

    async function relativepath(path) {
        return get('/fs/relativepath', path, 'text')
    }

    async function chooseopenfile(args) {
        /** open a dialog to choose a file
         *
         * @param args - a json object containing some or all of the following:
         *    title - the dialog title
         *    initialdir - the path to the initial directory
         *    initialfile - the initial filename
         *    filetypes - an array [(label, pattern), (label, patterns), ...] where label is the
         *      file type name (e.g. 'HTML') and patterns is the matching pattern (e.g. '*.html')
         *      probably comma separated.
         *    defaultextension - the extension to search for
         *
         * @returns the selected file path, '' if cancelled
         */
        return get('/ui/chooseopenfile', args, 'text')
    }

    async function choosesavefile(args) {
        /** open a dialog to save a file
         *
         * @param args - a json object containing some or all of the following:
         *    title - the dialog title
         *    initialdir - the path to the initial directory
         *    initialfile - the initial filename
         *    filetypes - an array [(label, pattern), (label, patterns), ...] where label is the
         *      file type name (e.g. 'HTML') and patterns is the matching pattern (e.g. '*.html')
         *      probably comma separated.
         *    defaultextension - the extension to search for
         *
         * @returns the selected file path, '' if cancelled
         */
        return get('/ui/choosesavefile', args, 'text')
    }

    async function choosefolder(args) {
        /** open a dialog to choose a folder
         *
         * @param args - a json object containing some or all of the following:
         *    title - the dialog title
         *    initialdir - the path to the initial directory
         *    initialfile - the initial filename ?
         *    filetypes - an array [(label, pattern), (label, patterns), ...] where label is the
         *      file type name (e.g. 'HTML') and patterns is the matching pattern (e.g. '*.html')
         *      probably comma separated.
         *    defaultextension - the extension to search for
         *
         * @returns the selected folder path, '' if cancelled
         */
        return get('/ui/choosefolder', args, 'text')
    }

    async function exit() {
        /** causes the server to shut down. Can be used when the page closes */
        get('/exit')
    }

    async function command(...args) {
        /** executes a command */
        get('/command', args)
    }

    return {
        readtext,
        readbinary,
        writefile,
        deletefile,
        readfolder,
        makefolder,
        deletefolder,
        copyfile,
        getstats,
        relativepath,
        chooseopenfile,
        choosesavefile,
        choosefolder,
        exit,
        command,
    }
})()
