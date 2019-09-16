#!/usr/bin/python3
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;
import sys
import argparse
import urllib.request
import errno
import shutil
import re
import os
import os.path
from zipfile import ZipFile, BadZipFile
import tarfile
from arsoft.utils import *
from arsoft.inifile import IniFile

package_list = {
    'trac': {
        'site': 'trac',
        'version': '1.2.5',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac',
        'debian-revision': 'minor',
        'orig-archive-format': 'tar.gz',
        'orig-archive-source': 'directory',
        'delete-files': ['trac/htdocs/js/jquery-ui-addons.js', 'trac/htdocs/js/jquery-ui.js', 'trac/htdocs/js/jquery.js', 'trac/htdocs/js/excanvas.js']
    },

    'AdvancedTicketWorkflowPlugin':  {
        'alias': 'advancedworkflow',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '1.2',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-advancedworkflow',
    },
    'trac-crashdump': {
        'alias': 'crashdump',
        'site': 'github-aroth-arsoft',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-crashdump',
    },
    'AnnouncerPlugin':  {
        'alias': 'announcer',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-announcer',
    },
    # graphix plugin is no longer requried for workflowadmin plugin
    'GraphvizPlugin':  {
        'disable': True,
        'alias': 'graphviz',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-graphviz',
    },
    'HudsonTracPlugin':  {
        'alias': 'hudson',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '1.2',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-hudson',
        'orig-archive-source': 'directory',
    },
    'IniAdminPlugin':  {
        'alias': 'iniadmin',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '0.11',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-iniadmin',
        'orig-archive-source': 'directory',
    },
    'MasterTicketsPlugin':  {
        'alias': 'mastertickets',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-mastertickets',
    },
    'NavAddPlugin': {
        'alias': 'navadd',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'trac_max_version': '1.3.2',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-navadd',
    },
    'TimingAndEstimationPlugin': {
        'alias': 'timingandestimation',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'branches/trac1.0',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-timingandestimation',
    },
    'TracWorkflowAdminPlugin': {
        'alias': 'workflowadmin',
        'site': 'trac-hacks',
        'repo_subdir': '0.12',
        'repo': 'svn',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-workflowadmin',
    },
    'XmlRpcPlugin': {
        'alias': 'xmlrpc',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-xmlrpc',
    },
    'CustomFieldAdminPlugin': {
        'alias': 'customfieldadmin',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '0.11',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-customfieldadmin',
    },
    'ClientsPlugin': {
        'alias': 'clients',
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': 'trunk',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-clients',
    },


}

site_list = {
    'trac': {
        'archive': 'tar.gz',
        'download': 'http://ftp.edgewall.com/pub/trac/Trac-${version}.tar.gz',
    },
    'trac-hacks': {
        'svn': 'https://trac-hacks.org/svn',
        'download': 'https://trac-hacks.org/browser',
        'revision': None,
    },
    'github-aroth-arsoft': {
        'git': 'https://github.com/aroth-arsoft',
    }
}

re_setup_py_version = re.compile(r'version\s*=\s*[\'"]([a-zA-Z0-9\.]+)[\'"]')

def get_html_title(url):
    def extract_html_title(data):
        from html.parser import HTMLParser
        class MyHTMLParser(HTMLParser):
            _path = []
            _title = None
            def handle_starttag(self, tag, attrs):
                self._path.append(tag)

            def handle_endtag(self, tag):
                self._path.pop()

            def handle_data(self, data):
                if len(self._path) > 1 and self._path[-1] == 'title':
                    self._title = data

        parser = MyHTMLParser()
        parser.feed(data)
        return parser._title

    hdr = {'User-Agent':'Mozilla/5.0', 'Accept': '*/*'}
    req = urllib.request.Request(url, headers=hdr)
    try:
        response = urllib.request.urlopen(req)
        if response.status == 200:
            data = response.read()      # a `bytes` object
            text = data.decode('utf-8') # a `str`; this step can't be used if data is binary
            #print(text)
            return extract_html_title(text)
        #elif response.status == 302:
            #newurl = response.geturl()
            #print('new url %s' % newurl)
    except urllib.error.HTTPError as e:
        if self._verbose:
            print('HTTP Error %s: %s' % (url, e))
        pass
    return None

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def rmdir_p(path):
    return shutil.rmtree(path, ignore_errors=False, onerror=None)

def copytree(src, dst, symlinks=False, ignore=None, copy_function=shutil.copy2,
             ignore_dangling_symlinks=False, ignore_existing_dst=False):
    """Recursively copy a directory tree.

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied. If the file pointed by the symlink doesn't
    exist, an exception will be added in the list of errors raised in
    an Error exception at the end of the copy process.

    You can set the optional ignore_dangling_symlinks flag to true if you
    want to silence this exception. Notice that this has no effect on
    platforms that don't support os.symlink.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    The optional copy_function argument is a callable that will be used
    to copy each file. It will be called with the source path and the
    destination path as arguments. By default, copy2() is used, but any
    function that supports the same signature (like copy()) can be used.

    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    if ignore_existing_dst:
        try:
            os.makedirs(dst)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(dst):
                pass
            else:
                raise
    else:
        os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.islink(srcname):
                linkto = os.readlink(srcname)
                if symlinks:
                    # We can't just leave it to `copy_function` because legacy
                    # code with a custom `copy_function` may rely on copytree
                    # doing the right thing.
                    os.symlink(linkto, dstname)
                    shutil.copystat(srcname, dstname, follow_symlinks=not symlinks)
                else:
                    # ignore dangling symlink if the flag is on
                    if not os.path.exists(linkto) and ignore_dangling_symlinks:
                        continue
                    # otherwise let the copy occurs. copy2 will raise an error
                    if os.path.isdir(srcname):
                        copytree(srcname, dstname, symlinks, ignore,
                                 copy_function, ignore_existing_dst=ignore_existing_dst)
                    else:
                        copy_function(srcname, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore, copy_function, ignore_existing_dst=ignore_existing_dst)
            else:
                # Will raise a SpecialFileError for unsupported file types
                copy_function(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        shutil.copystat(src, dst)
    except OSError as why:
        # Copying file access times may fail on Windows
        if getattr(why, 'winerror', None) is None:
            errors.append((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)
    return dst

def remove_obsolete_files(src, dst, ignore=None):
    names = os.listdir(dst)
    if ignore is not None:
        ignored_names = ignore(dst, names)
    else:
        ignored_names = set()

    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(dstname):
                remove_obsolete_files(srcname, dstname, ignore)
            if not os.path.exists(srcname):
                print('remove %s' %dstname)
                if os.path.isfile(dstname):
                    os.unlink(dstname)
                else:
                    rmdir_p(dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname, dstname, str(why)))
    if errors:
        raise shutil.Error(errors)
    return dst

def copy_and_overwrite(from_path, to_path):
    def _copy_and_overwrite(src, dst):
        shutil.copy2(src, dst)
    ret = False
    try:
        copytree(from_path, to_path, copy_function=_copy_and_overwrite, ignore_existing_dst=True)
        ret = True
    except shutil.Error as e:
        print('Copy failed: %s' % e, file=sys.stderr)

    remove_obsolete_files(from_path, to_path, ignore=shutil.ignore_patterns('debian', '.pc', '.git*'))
    return ret

def git_archive_gz(repo_dir, tar_file, prefix):
    f = open(tar_file, 'w')
    gitproc = subprocess.Popen(['git', 'archive', '--format', 'tar', '--prefix=%s/' % prefix, 'HEAD'], stdout=subprocess.PIPE, cwd=repo_dir)
    gzip_proc = subprocess.Popen(['gzip'],stdin=gitproc.stdout, stdout=f)
    gitproc.stdout.close() # enable write error in gzip if git dies
    stdoutdata, stderrdata = gzip_proc.communicate()
    sts = gzip_proc.returncode
    f.close()
    return True if sts == 0 else False

def git_archive_xz(repo_dir, tar_file, prefix):
    f = open(tar_file, 'w')
    gitproc = subprocess.Popen(['git', 'archive', '--format', 'tar', '--prefix=%s/' % prefix, 'HEAD'], stdout=subprocess.PIPE, cwd=repo_dir)
    gzip_proc = subprocess.Popen(['xz', '-c' ],stdin=gitproc.stdout, stdout=f)
    gitproc.stdout.close() # enable write error in gzip if git dies
    stdoutdata, stderrdata = gzip_proc.communicate()
    sts = gzip_proc.returncode
    f.close()
    return True if sts == 0 else False

def extract_archive(archive, dest_dir):
    ret = False
    b = os.path.basename(archive)
    b, last_ext = os.path.splitext(b)
    if last_ext == '.zip':
        try:
            with ZipFile(archive, 'r') as zipObj:
                # Extract all the contents of zip file in different directory
                zipObj.extractall(dest_dir)
            ret = True
        except BadZipFile as e:
            print('ZIP file %s error: %s' % (archive, e), file=sys.stderr)
    elif last_ext == '.gz' or last_ext == '.bz2' or last_ext == '.xz':
        b, second_ext = os.path.splitext(b)
        if second_ext == '.tar':
            try:
                with tarfile.open(archive, 'r') as tarObj:
                    # Extract all the contents of tar file in different directory
                    tarObj.extractall(dest_dir)
                ret = True
            except tarfile.TarError as e:
                print('Tar file %s error: %s' % (archive, e), file=sys.stderr)
    #print('extract_archive ret->%s %i' % (archive, ret))
    return ret

def make_tarfile(repo_dir, tar_file, prefix, format=None):
    ret = False
    if format is None:
        b = os.path.basename(tar_file)
        b, last_ext = os.path.splitext(b)
        format = last_ext[1:]
    with tarfile.open(tar_file, "w:%s" % format) as tar:
        tar.add(repo_dir, arcname=prefix)
        ret = True
    return ret

def increment_debian_revision(rev, strategy):
    e = rev.split('.')
    if strategy == 'minor':
        if len(e) < 2:
            e.append('0')
    try:
        num = int(e[-1]) + 1
    except ValueError:
        num = 0 if strategy != 'minor' else 1
    e[-1] = str(num)
    return '.'.join(e)


class trac_package_update_app(object):
    def __init__(self):
        self._verbose = False

    def _get_latest_revisions(self):
        for name, details in site_list.items():
            svn = details.get('svn', None)
            if svn is not None:
                title = get_html_title(svn)
                idx = title.find('Revision')
                if idx >= 0:
                    end = title.find(':', idx + 8)
                    rev = int(title[idx + 8: end])
                    site_list[name]['revision'] = rev
        return True

    def _load_package_list(self):
        for name, details in package_list.items():
            if name not in self._packages:
                #if self._verbose:
                    #print('Skip package %s' % name)
                continue
            site = site_list.get(details.get('site', None), None)
            if site:
                site_rev = site.get('revision', None)
                site_archive = site.get('archive', None)
                site_download = site.get('download', None)
                if site_archive is None:
                    site_git = site.get('git', None)
                    url = None
                    if site_download is not None:
                        url = site_download + '/' + name.lower() + '/'
                    elif site_git is not None:
                        url = site_git + '/' + name.lower() + '/'
                    repo_subdir = details.get('repo_subdir', None)
                    if repo_subdir:
                        url += repo_subdir + '/'
                    if site_git is None:
                        url += '?format=zip'
                        if site_rev is not None:
                            url += '&rev=%s' % site_rev
                    package_list[name]['site_download_url'] = url
                elif site_download is not None:
                    url = site_download
                    package_list[name]['site_download_url'] = url

    def _list(self):
        for name, details in site_list.items():
            print('Site %s' % name)
            site_rev = details.get('revision', None)
            site_git = details.get('git', None)
            site_archive = details.get('archive', None)
            site_download = details.get('download', None)
            if site_rev is not None:
                print('  Revision: %s' % site_rev)
            elif site_archive:
                print('  Download: %s' % site_download)
                print('  Archive: %s' % site_archive)
            elif site_git:
                print('  Git: %s' % site_git)

        for name, details in package_list.items():
            if name not in self._packages:
                continue
            if details.get('disable', False):
                continue
            url = details.get('site_download_url')
            version = details.get('version', None)
            if url and version is not None:
                url = url.replace('${version}', version)
            print('%s' % name)
            print('  URL: %s' % url)
        return 0

    def _download_pkgs(self):
        ret = True
        mkdir_p(self._download_dir)
        for name, details in package_list.items():
            if name not in self._packages:
                continue
            if details.get('disable', False):
                continue
            print('%s' % name)
            site = site_list.get(details.get('site', None), None)
            if site:
                url = details.get('site_download_url')
                delete_files = details.get('delete-files', [])
                version = details.get('version', None)
                if version is not None:
                    url = url.replace('${version}', version)
                site_rev = site.get('revision', None)
                site_download = site.get('download', None)
                site_archive = site.get('archive', None)
                if site_download is None:
                    download_ok = True
                else:
                    dest_format = 'zip'
                    if site_archive is None:
                        filename = name.lower()
                        if site_rev is not None:
                            filename += '_rev%s' % site_rev
                        filename += '.zip'
                    else:
                        filename = name.lower() + '_%s.%s' % (version, site_archive)
                        dest_format = site_archive
                    download_ok = False

                    dest = os.path.join(self._download_dir, filename)
                    if os.path.isfile(dest):
                        if self._force:
                            os.unlink(dest)
                        else:
                            download_ok = True
                    if not download_ok:
                        #print(url)
                        try:
                            urllib.request.urlretrieve(url, dest)
                            download_ok = True
                        except urllib.error.HTTPError as ex:
                            print('HTTP error %s for %s' % (ex, url))
                    elif self._verbose:
                        print('Download file %s already exists.' % dest)

                if download_ok and site_archive and delete_files:
                    download_subdir = os.path.basename(url)
                    i = download_subdir.find(site_archive)
                    if i >= 0:
                        download_subdir = download_subdir[0:i]
                        if download_subdir[-1] == '.':
                            download_subdir = download_subdir[0:-1]

                    download_ok = False
                    pkg_download_tmp_dir = os.path.join(self._download_dir, name.lower() + '.tmp')
                    if self._verbose:
                        print('Extract to %s' % pkg_download_tmp_dir)
                    # extract to temp directory, delete the files and re-package
                    if extract_archive(dest, pkg_download_tmp_dir):
                        prefix = download_subdir
                        base_dir = os.path.join(pkg_download_tmp_dir, download_subdir)
                        for f in delete_files:
                            full = os.path.join(base_dir, f)
                            if os.path.exists(full):
                                try:
                                    os.unlink(full)
                                except IOError as e:
                                    print('Unable to delete %s: %s' % (full, e), file=sys.stderr)
                        download_ok = make_tarfile(base_dir, dest, prefix=prefix)
                        if not download_ok:
                            print('Failed to create tar archive %s from %s' % (dest, base_dir), file=sys.stderr)

                if site_download is None:
                    # No download required
                    pass
                elif download_ok:
                    pkg_download_dir = os.path.join(self._download_dir, name.lower())
                    pkg_download_tag_file = os.path.join(self._download_dir, '.' + name.lower() + '.tag')

                    # Extract all the contents of zip file in different directory
                    if not extract_archive(dest, pkg_download_dir):
                        print('Failed to extract %s to %s' % (dest, pkg_download_dir), file=sys.stderr)
                        ret = False

                    f = IniFile(pkg_download_tag_file)
                    if url is not None:
                        f.set(None, 'url', url)
                    if site_rev is not None:
                        f.set(None, 'rev', site_rev)
                    if site_archive is not None:
                        f.set(None, 'archive', site_archive)
                    f.save(pkg_download_tag_file)
                    f.close()
                else:
                    print('Download failed %s' % (name), file=sys.stderr)
                    ret = False
        return ret

    def _update_package_repo(self):
        ret = True
        mkdir_p(self._repo_dir)
        for name, details in package_list.items():
            if name not in self._packages:
                continue
            if details.get('disable', False):
                continue
            pkgrepo = details.get('pkgrepo', '')
            repo_ok = False
            if pkgrepo == 'git':
                pkgrepo_dir = details.get('pkgrepo_dir', None)
                if pkgrepo_dir:
                    repo_dir = os.path.join(self._repo_dir, pkgrepo_dir)
                    repo_ok = os.path.isdir(repo_dir)
                else:
                    pkgrepo_url = details.get('pkgrepo_url', None)
                    repo_dir = os.path.join(self._repo_dir, name.lower())
                    if os.path.isdir(repo_dir):
                        try:
                            (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'pull', 'origin'], cwd=repo_dir)
                        except FileNotFoundError as ex:
                            print('Cannot execute git.', file=sys.stderr)
                            sts = -1
                        print(stdoutdata, stderrdata)
                    else:
                        try:
                            (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'clone', pkgrepo_url, repo_dir], cwd=repo_dir)
                        except FileNotFoundError as ex:
                            print('Cannot execute git.', file=sys.stderr)
                            sts = -1
                        print(stdoutdata, stderrdata)
                    repo_ok = True if sts == 0 else False

            if repo_ok:
                print('Repository %s ok' % repo_dir)
                download_subdir = details.get('repo_subdir', name.lower())
                pkg_download_tag_file = os.path.join(self._download_dir, '.' + name.lower() + '.tag')
                rev = None
                url = None
                archive = None
                if os.path.isfile(pkg_download_tag_file):
                    f = IniFile(pkg_download_tag_file)
                    rev = f.getAsInteger(None, 'rev', None)
                    archive = f.get(None, 'archive', None)
                    url = f.get(None, 'url', None)
                    f.close()
                if archive is not None:
                    download_subdir = os.path.basename(url)
                    i = download_subdir.find(archive)
                    if i >= 0:
                        download_subdir = download_subdir[0:i]
                        if download_subdir[-1] == '.':
                            download_subdir = download_subdir[0:-1]

                if self._verbose:
                    print(self._download_dir, name.lower(), '' if download_subdir is None else download_subdir)
                pkg_download_dir = os.path.join(self._download_dir, name.lower(), '' if download_subdir is None else download_subdir)
                if os.path.isdir(pkg_download_dir):
                    print('Update %s from %s' % (name.lower(), pkg_download_dir))

                    if copy_and_overwrite(pkg_download_dir, repo_dir):

                        delete_files = details.get('delete-files', [])
                        if delete_files:
                            for f in delete_files:
                                full = os.path.join(repo_dir, f)
                                if os.path.exists(full):
                                    try:
                                        os.unlink(full)
                                    except IOError as e:
                                        print('Unable to delete %s: %s' % (full, e), file=sys.stderr)

                        pc_dir = os.path.join(repo_dir, '.pc')
                        if os.path.isdir(pc_dir):
                            if self._verbose:
                                print('Delete directory %s' % (pc_dir))
                            rmdir_p(pc_dir)

                        debian_package_name = None
                        debian_package_version = None
                        debian_package_orig_version = None
                        debian_package_update_ok = False
                        debian_revision = None
                        setup_py_version = None
                        setup_py = os.path.join(repo_dir, 'setup.py')
                        try:
                            f = open(setup_py, 'r')
                            for line in f:
                                m = re_setup_py_version.search(line)
                                if m:
                                    setup_py_version = m.group(1)
                                    break
                            f.close()
                        except IOError as e:
                            print('Unable to open %s: %s' % (setup_py, e), file=sys.stderr)
                            pass

                        if setup_py_version:

                            if rev and url:
                                commit_msg = 'Automatic update %s from %s revision %i' % (setup_py_version, url, rev)
                            else:
                                commit_msg = 'Automatic update %s' % setup_py_version

                            dch_filename = os.path.join(repo_dir, 'debian/changelog')
                            dch_version = None
                            try:
                                import debian.changelog
                                from textwrap import TextWrapper
                                f = open(dch_filename, 'r')
                                dch = debian.changelog.Changelog(f)
                                f.close()
                                debian_package_name = dch.package
                                old_version = str(dch.version)
                                is_dfsg = old_version.find('dfsg') != -1
                                if rev:
                                    debian_package_orig_version = setup_py_version + '+svn%i' % rev
                                elif is_dfsg:
                                    debian_package_orig_version = setup_py_version + '+dfsg'
                                else:
                                    debian_package_orig_version = setup_py_version
                                new_version = debian_package_orig_version + '-'
                                if old_version.startswith(new_version):
                                    i = old_version.find('-')
                                    if i:
                                        debian_revision = old_version[i+1:] if i else 0
                                else:
                                    debian_revision = '0'

                                debian_revision = increment_debian_revision(debian_revision, strategy=details.get('debian-revision', 'major'))
                                new_version = new_version + debian_revision

                                debian_package_version = new_version
                                dch.new_block(
                                    package=debian_package_name,
                                    version=debian_package_version,
                                    distributions=self._distribution,
                                    urgency=dch.urgency,
                                    author="%s <%s>" % debian.changelog.get_maintainer(),
                                    date=debian.changelog.format_date()
                                )
                                wrapper = TextWrapper()
                                wrapper.initial_indent    = "  * "
                                wrapper.subsequent_indent = "    "
                                dch.add_change('')
                                for l in wrapper.wrap(commit_msg):
                                    dch.add_change(l)
                                dch.add_change('')
                                f = open(dch_filename, 'w')
                                f.write(str(dch))
                                #print(dch)
                                f.close()
                                debian_package_update_ok = True
                            except IOError as e:
                                print('Unable to open %s: %s' % (dch_filename, e), file=sys.stderr)
                                pass
                        else:
                            print('Failed to get version from %s.' % setup_py, file=sys.stderr)
                            ret = False

                        if debian_package_update_ok:

                            if pkgrepo == 'git':
                                try:
                                    (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'commit', '-am', commit_msg], cwd=repo_dir)
                                except FileNotFoundError as ex:
                                    print('Cannot execute git.', file=sys.stderr)
                                    ret = False
                                    sts = -1

                                orig_archive_format = details.get('orig-archive-format', 'tar.xz')
                                orig_archive_source = details.get('orig-archive-source', 'git')

                                prefix = debian_package_name + '-' + debian_package_orig_version
                                pkgfile = os.path.join(repo_dir, '..', debian_package_name + '_' + debian_package_orig_version + '.orig.' + orig_archive_format)
                                if orig_archive_source == 'git':
                                    if orig_archive_format == 'tar.xz':
                                        if not git_archive_xz(repo_dir, pkgfile, prefix):
                                            print('Failed to create %s.' % pkgfile, file=sys.stderr)
                                            ret = False
                                    elif orig_archive_format == 'tar.gz':
                                        if not git_archive_gz(repo_dir, pkgfile, prefix):
                                            print('Failed to create %s.' % pkgfile, file=sys.stderr)
                                            ret = False
                                    else:
                                        print('Invalid package orig archive format \'%s\' specified.' % orig_archive_format, file=sys.stderr)
                                        ret = False
                                elif orig_archive_source == 'directory':
                                    i = orig_archive_format.find('.')
                                    if i > 0:
                                        format = orig_archive_format[i+1:]
                                    else:
                                        format = 'xz'
                                    make_tarfile(repo_dir, pkgfile, prefix, format=format)

                                else:
                                    print('Invalid package orig archive source \'%s\' specified.' % orig_archive_source, file=sys.stderr)
                                    ret = False
                        else:
                            if self._verbose:
                                print('Debian package update failed.', file=sys.stderr)
                            ret = False
                    else:
                        print('Failed to copy to %s' % repo_dir, file=sys.stderr)
                        ret = False
            else:
                print('Repository %s failed' % repo_dir, file=sys.stderr)
                ret = False
        return ret

    def _ppa_publish(self):
        ret = True
        for name, details in package_list.items():
            if name not in self._packages:
                continue
            if details.get('disable', False):
                continue

            pkgrepo = details.get('pkgrepo', '')
            repo_ok = False
            if pkgrepo == 'git':
                pkgrepo_dir = details.get('pkgrepo_dir', None)
                if pkgrepo_dir:
                    repo_dir = os.path.join(self._repo_dir, pkgrepo_dir)
                    repo_ok = os.path.isdir(repo_dir)
                else:
                    pkgrepo_url = details.get('pkgrepo_url', None)
                    repo_dir = os.path.join(self._repo_dir, name.lower())
                    repo_ok = os.path.isdir(repo_dir)
            if repo_ok:
                print('Publish package on PPA from %s' % repo_dir)
                try:
                    (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['ppa_publish'], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, cwd=repo_dir)
                    if sts != 0:
                        print('ppa_publish failed:\n%s' % stderrdata, file=sys.stderr)
                except FileNotFoundError as ex:
                    print('Cannot execute ppa_publish.', file=sys.stderr)
                    ret = False

        return ret

    def main(self):
        #=============================================================================================
        # process command line
        #=============================================================================================
        parser = argparse.ArgumentParser(description='update/generate trac packages')
        parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='enable verbose output of this script.')
        parser.add_argument('-f', '--force', dest='force', action='store_true', help='force re-download of packages.')
        parser.add_argument('-l', '--list', dest='list', action='store_true', help='show list of all packages.')
        parser.add_argument('-np', '--no-publish', dest='no_publish', action='store_true', help='do not publish packages.')
        parser.add_argument('-u', '--update', dest='update', action='store_true', help='update the package repositories.')
        parser.add_argument('-p', '--package', dest='packages', nargs='*', help='select packages to process (default all)')

        args = parser.parse_args()
        self._verbose = args.verbose
        self._force = args.force
        self._no_publish = args.no_publish

        base_dir = os.path.abspath(os.getcwd())
        self._download_dir = os.path.join(base_dir, 'download')
        self._repo_dir = os.path.join(base_dir, 'repo')
        if args.packages:
            self._packages = []
            available_packages = {}
            for name, details in package_list.items():
                available_packages[name.lower()] = name
                alias = details.get('alias', None)
                if alias is not None:
                    available_packages[alias.lower()] = name
            got_unknown_package = False
            for p in args.packages:
                pkg_name = p.lower()
                if pkg_name in available_packages:
                    real_name = available_packages[pkg_name]
                    self._packages.append(real_name)
                else:
                    got_unknown_package = True
                    print('Unknown package %s specified.' % p, file=sys.stderr)
            if got_unknown_package:
                return 1
        else:
            self._packages = package_list.keys()

        try:
            import debian
        except ImportError:
            print('Debian python extension not available. Please install python3-debian.', file=sys.stderr)
            return 2

        lsb_release = IniFile('/etc/lsb-release')
        self._distribution = lsb_release.get(None, 'DISTRIB_CODENAME', 'unstable')
        lsb_release.close()

        self._get_latest_revisions()
        self._load_package_list()

        if args.list:
            ret = self._list()
        elif args.update:
            if self._download_pkgs():
                if self._update_package_repo():
                    if self._no_publish:
                        ret = 0
                    else:
                        if self._ppa_publish():
                            ret = 0
                        else:
                            ret = 5
                else:
                    ret = 4
            else:
                ret = 3
        else:
            ret = 0

        return ret


if __name__ == "__main__":
    app =  trac_package_update_app()
    sys.exit(app.main())
