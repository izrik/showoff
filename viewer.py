#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LICENSE {{{
"""
Showoff - Webbased photo album software

Copyright (c) 2010 by Jochem Kossen <jochem.kossen@gmail.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above
   copyright notice, this list of conditions and the following
   disclaimer in the documentation and/or other materials provided
   with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR#{{{# }}}
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

This is the viewer application code for showoff. It's only used for
viewing content, not manipulation.

"""
# }}}

# IMPORTS {{{
from flask import Flask, abort, render_template, send_from_directory, session, request
from controllers import PageController, ImageController
from functools import wraps
from libshowoff import Show
from forms import LoginForm
import os
# }}}

# APP INITIALIZATION {{{
app = Flask(__name__, static_path=None, template_folder='templates/viewer')
app.config.from_pyfile('config.py')
app.config.from_envvar('SHOWOFF_VIEWER_CONFIG', silent=True)
# }}}

# HELPER FUNCTIONS {{{
def get_show(album, page, endpoint, template):
    controller = PageController(app)
    return controller.act('get_show', album=album, page=page,
                          endpoint=endpoint, template=template)

def view(rule, **options):
    """ Decorator for views """
    complete_rule = '/%s%s' % (app.config['VIEWER_PREFIX'],
            app.config['VIEWER_ROUTES'][rule])

    def decorator(f):
        app.add_url_rule(complete_rule, None, f, **options)
        return f
    return decorator

def render_themed(template, **options):
    """ Render template from a configured subdir to implement themes """
    template_path = os.path.join(app.config['THEME'], template)
    return render_template(template_path, **options)

def login_required(fun):
    """Decorator for functions which require an authorized user"""
    @wraps(fun)
    def decorated_function(album, *args, **kwargs):
        """Decorated function"""
        if need_authentication(album):
            return login(album)
        return fun(album, *args, **kwargs)

    return decorated_function

def need_authentication(album):
    show = Show(app, album)
    if (show.get_setting('require_authentication') == 'yes'):
        if session.get('username') and (session.get('album') == album):
            return False
        else:
            return True
    return False
# }}}

# TEMPLATE TAGS {{{
@app.template_filter('exif_table')
def get_exif_table(exif):
    table = '<table>'
    for line in exif:
        table = table + '<tr><td>' + line.replace('|', '</td><td>') + '</td></tr>'
    table = table + '</table>'
    return table
# }}}

# VIEWS {{{
@view('login', methods=['GET','POST'])
def login(album):
    """Check user credentials and initialize session"""
    form = LoginForm()
    show = Show(app, album)

    if request.method == 'POST':
        form = LoginForm(request.form)
        if form.validate():
            if show.check_auth(request.form['username'], app.config['SECRET_KEY'], request.form['password']):
                session.clear()
                session['username'] = request.form['username']
                session['album'] = album
                return list(album, 1)

    return render_themed('login.html', album=album, form=form)

@view('static_files')
def static_files(filename):
    """Send static files such as style sheets, JavaScript, etc."""
    static_path = os.path.join(app.root_path, 'templates', 'viewer',
                               app.config['THEME'], 'static')
    return send_from_directory(static_path, filename)

@view('get_image')
@login_required
def get_image(album, filename, size=None):
    controller = ImageController(app)
    return controller.act('get', album, filename, size)

@view('image_page')
@login_required
def image_page(album, filename):
    controller = PageController(app)
    return controller.act('image_info', album, filename)

@view('show')
@view('list')
@login_required
def list(album, page, template='list'):
    if template in app.config['VIEWER_LIST_TEMPLATES']:
        return get_show(album, page, 'list', template)
    else:
        abort(404)

@view('show_slideshow')
@login_required
def show_slideshow(album, page):
    controller = PageController(app)
    return controller.act('slideshow', album, page, 'show_slideshow',
                          'slideshow.html')

@view('album')
@login_required
def show_album(album):
    """Render first page of album"""
    return list(album, 1)

@view('index')
def show_index():
    controller = PageController(app)
    return controller.act('index')
# }}}

# MAIN RUN LOOP {{{
if __name__ == '__main__':
    app.run(host=app.config['VIEWER_HOST'], port=app.config['VIEWER_PORT'])
# }}}

