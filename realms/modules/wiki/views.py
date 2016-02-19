import itertools
import sys
from flask import abort, g, render_template, request, redirect, Blueprint, flash, url_for, current_app
from flask.ext.login import login_required, current_user
from realms.lib.util import to_canonical, remove_ext, gravatar_url
from .models import PageNotFound
import re

blueprint = Blueprint('wiki', __name__)


@blueprint.route("/_commit/<sha>/<path:name>")
def commit(name, sha):
    if current_app.config.get('PRIVATE_WIKI') and current_user.is_anonymous():
        return current_app.login_manager.unauthorized()

    cname = to_canonical(name)

    data = g.current_wiki.get_page(cname, sha=sha)

    if not data:
        abort(404)

    return render_template('wiki/page.html', name=name, page=data, commit=sha)


@blueprint.route(r"/_compare/<path:name>/<regex('\w+'):fsha><regex('\.{2,3}'):dots><regex('\w+'):lsha>")
def compare(name, fsha, dots, lsha):
    if current_app.config.get('PRIVATE_WIKI') and current_user.is_anonymous():
        return current_app.login_manager.unauthorized()

    diff = g.current_wiki.compare(name, fsha, lsha)
    return render_template('wiki/compare.html',
                           name=name, diff=diff, old=fsha, new=lsha)


@blueprint.route("/_revert", methods=['POST'])
@login_required
def revert():
    cname = to_canonical(request.form.get('name'))
    commit = request.form.get('commit')
    message = request.form.get('message', "Reverting %s" % cname)

    if not current_app.config.get('ALLOW_ANON') and current_user.is_anonymous():
        return dict(error=True, message="Anonymous posting not allowed"), 403

    if cname in current_app.config.get('WIKI_LOCKED_PAGES'):
        return dict(error=True, message="Page is locked"), 403

    try:
        sha = g.current_wiki.revert_page(cname,
                                         commit,
                                         message=message,
                                         username=current_user.username,
                                         email=current_user.email)
    except PageNotFound as e:
        return dict(error=True, message=e.message), 404

    if sha:
        flash("Page reverted")

    return dict(sha=sha)


@blueprint.route("/_history/<path:name>")
def history(name):
    if current_app.config.get('PRIVATE_WIKI') and current_user.is_anonymous():
        return current_app.login_manager.unauthorized()

    hist = g.current_wiki.get_history(name)
    for item in hist:
        item['gravatar'] = gravatar_url(item['author_email'])
    return render_template('wiki/history.html', name=name, history=hist)


@blueprint.route("/_edit/<path:name>")
@login_required
def edit(name):
    cname = to_canonical(name)
    page = g.current_wiki.get_page(name)

    if not page:
        # Page doesn't exist
        return redirect(url_for('wiki.create', name=cname))

    name = remove_ext(page['path'])
    g.assets['js'].append('editor.js')

    return render_template('wiki/edit.html',
                           name=name,
                           content=page.get('data'),
                           info=page.get('info'),
                           sha=page.get('sha'),
                           partials=page.get('partials'))


@blueprint.route("/_create/", defaults={'name': None})
@blueprint.route("/_create/<path:name>")
@login_required
def create(name):
    cname = to_canonical(name) if name else ""
    if cname and g.current_wiki.get_page(cname):
        # Page exists, edit instead
        return redirect(url_for('wiki.edit', name=cname))

    g.assets['js'].append('editor.js')
    return render_template('wiki/edit.html',
                           name=cname + '/',
                           content="",
                           info={})


def _get_subdir(path, depth):
    parts = path.split('/', depth)
    if len(parts) > depth:
        return parts[-2]


def _tree_index(items, path=""):
    depth = len(path.split("/"))
    items = filter(lambda x: x['name'].startswith(path), items)
    items = sorted(items, key=lambda x: x['name'])
    for subdir, items in itertools.groupby(items, key=lambda x: _get_subdir(x['name'], depth)):
        if not subdir:
            for item in items:
                yield dict(item, dir=False)
        else:
            size = 0
            ctime = sys.maxint
            mtime = 0
            for item in items:
                size += item['size']
                ctime = min(item['ctime'], ctime)
                mtime = max(item['mtime'], mtime)
            yield dict(name=path + subdir + "/",
                       mtime=mtime,
                       ctime=ctime,
                       size=size,
                       dir=True)

# Build the proper sidebar for the current directory
def _build_sidebar(path = ""):
    items = g.current_wiki.get_index()
    if path:
        path = to_canonical(path) + "/"
    # append always as first element the back link (go up by one level of directory)
    sidebar = [ dict(name = 'Back', dir = False, link = "../home") ]
    # get the tree for the current directory (the files belonging to the current subdir plus the subdir of level 1)
    for item in _tree_index(items, path=path):
        name = ''
        link = ''
        # if we are analyzing a directory 
        if item['dir']:
            # the name is the last word before the last '/' (we have to take the last but one because the returned name has the form /sub1/sub2/sub3/, 
            # if we would take the last the result will be '')
            name = item["name"].split('/')[-2]
            # append the home keyword in order to redirect the user at tjhehomepage of the chosen subdir
            link = "/" + item["name"] + "home"
        # if we are analyzing a file
        else:
            # the name i simly the last word after the last "/""
            name = item["name"].split('/')[-1]
            link = "/" + item["name"]          
        sidebar.append(dict(name = name, dir = item['dir'], link = link))
    return sidebar            



@blueprint.route("/_index", defaults={"path": ""})
@blueprint.route("/_index/<path:path>")
def index(path):
    if current_app.config.get('PRIVATE_WIKI') and current_user.is_anonymous():
        return current_app.login_manager.unauthorized()

    items = g.current_wiki.get_index()
    if path:
        path = to_canonical(path) + "/"

    return render_template('wiki/index.html', index=_tree_index(items, path=path), path=path)



@blueprint.route("/upload", methods=['POST'])
def upload_handler():
    if request.method == 'POST':
        #get the chunk and the number of chunks if they are defined (only if the client send the image in chunk mode)
        chunk = request.form['chunk'] if 'chunk' in request.form else None
        chunks = request.form['chunks'] if 'chunks' in request.form else None
        #get the information relative to the file
        file_name = request.form['name']
        file_path = current_app.config.get('UPLOAD_FOLDER') + file_name
        # if we receive the first chunk lets's open the file as a new one
        # otherwise open it in append mode in order to write the next chunk
        tmp_file = open(file_path, "wb" if chunk == 0 else "ab")

        if tmp_file:
            # get the content of he received chunk
            in_file = request.files['file']
            if in_file:
                # update the file
                tmp_file.write(in_file.read())

            tmp_file.close()

        return dict(success = request.form)

@blueprint.route("/debug")
def debug_route():
    content ="""
            <img src='/static/img/uploads/img1.png' class='image-fit-100'/>
            <img src='/static/img/uploads/img2.png' class='image-fit-100'/>
            <img src='/static/img/uploads/img3.png' class='image-fit-100'/>
            """
    img_list = re.findall("src\s*=\s*'(.+?)'", content)
    new_list = []
    for img in img_list:
        new_list.append(re.sub("uploads", "uploads_tmp", img))
    return new_list


@blueprint.route("/<path:name>", methods=['POST', 'PUT', 'DELETE'])
@login_required
def page_write(name):
    cname = to_canonical(name)
    
    if not cname:
        return dict(error=True, message="Invalid name")

    if not current_app.config.get('ALLOW_ANON') and current_user.is_anonymous():
        return dict(error=True, message="Anonymous posting not allowed"), 403

    if request.method == 'POST':
        # Create
        create_cname = to_canonical(request.form['name'])

        # if the page already exist we don't want an override
        if g.current_wiki.get_page(create_cname):
            return dict(error=True, message="Page already exists"), 403

        if cname in current_app.config.get('WIKI_LOCKED_PAGES'):
            return dict(error=True, message="Page is locked"), 403

        sha = g.current_wiki.write_page(create_cname,
                                        request.form['content'],
                                        message=request.form['message'],
                                        create=True,
                                        username=current_user.username,
                                        email=current_user.email)

    elif request.method == 'PUT':
        edit_cname = to_canonical(request.form['name'])

        if edit_cname in current_app.config.get('WIKI_LOCKED_PAGES'):
            return dict(error=True, message="Page is locked"), 403

        if edit_cname != cname:
            g.current_wiki.rename_page(cname, edit_cname)

        sha = g.current_wiki.write_page(edit_cname,
                                        request.form['content'],
                                        message=request.form['message'],
                                        username=current_user.username,
                                        email=current_user.email)

        return dict(sha=sha)

    elif request.method == 'DELETE':
        # DELETE
        if cname in current_app.config.get('WIKI_LOCKED_PAGES'):
            return dict(error=True, message="Page is locked"), 403

        sha = g.current_wiki.delete_page(cname,
                                         username=current_user.username,
                                         email=current_user.email)

    return dict(sha=sha)
    
           

# the homepage is not part of the wiki anymore
@blueprint.route("/")
def home_page():
   return render_template('wiki/homepage.html')

@blueprint.route("/", defaults={'name': 'home'})
@blueprint.route("/<path:name>")
def page(name):
    if current_app.config.get('PRIVATE_WIKI') and current_user.is_anonymous():
        return current_app.login_manager.unauthorized()

    cname = to_canonical(name)
    if cname != name:
        return redirect(url_for('wiki.page', name=cname))

    data = g.current_wiki.get_page(cname)

    path = cname
    # get the path to the current file without its name
    if '/' in cname:
        path = cname[:cname.rfind("/")]
    # buil the sidebar for the retreived path
    sidebar = _build_sidebar(path=path)

    if data:
        return render_template('wiki/page.html', name=cname, page=data, sidebar=sidebar, partials=data.get('partials'), path=path)
    else:
         abort(404)


