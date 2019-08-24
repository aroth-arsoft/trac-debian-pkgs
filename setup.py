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
from zipfile import ZipFile
from arsoft.utils import *
from arsoft.inifile import IniFile

package_list = {
    'AdvancedTicketWorkflowPlugin':  {
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '1.2',
        'pkgrepo': 'git',
        'pkgrepo_dir': 'trac-advancedworkflow',
    },
}

site_list = {
    'trac-hacks': {
        'svn': 'https://trac-hacks.org/svn',
        'download': 'https://trac-hacks.org/browser',
        'revision': None,
    },
}

re_setup_py_version = re.compile(r'version=[\'"]([a-zA-Z0-9\.]+)[\'"]')

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

def copy_and_overwrite(from_path, to_path):
    def _copy_and_overwrite(src, dst):
        shutil.copy2(src, dst)
    ret = False
    try:
        copytree(from_path, to_path, copy_function=_copy_and_overwrite, ignore_existing_dst=True)
        ret = True
    except shutil.Error as e:
        print('Copy failed: %s' % e, file=sys.stderr)
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
            site = site_list.get(details.get('site', None), None)
            if site:
                site_rev = site.get('revision', None)
                url = site.get('download') + '/' + name.lower() + '/'
                repo_subdir = details.get('repo_subdir', None)
                if repo_subdir:
                    url += repo_subdir + '/'
                url += '?format=zip'
                if site_rev is not None:
                    url += '&rev=%s' % site_rev
                package_list[name]['site_download_url'] = url

    def _list(self):
        for name, details in site_list.items():
            print('Site %s' % name)
            print('  Revision: %s' % details.get('revision'))
        for name, details in package_list.items():
            print('%s' % name)
            print('  URL: %s' % details.get('url'))
        return 0

    def _download_pkgs(self):
        mkdir_p(self._download_dir)
        for name, details in package_list.items():
            print('%s' % name)
            site = site_list.get(details.get('site', None), None)
            if site:
                url = details.get('site_download_url')
                site_rev = site.get('revision', None)
                filename = name.lower()
                if site_rev is not None:
                    filename += '_rev%s' % site_rev
                filename += '.zip'
                dest = os.path.join(self._download_dir, filename)
                if os.path.isfile(dest):
                    os.unlink(dest)
                #print(url)
                download_ok = False
                try:
                    urllib.request.urlretrieve(url, dest)
                    download_ok = True
                except urllib.error.HTTPError as ex:
                    print('HTTP error %s for %s' % (ex, url))
                if download_ok:
                    pkg_download_dir = os.path.join(self._download_dir, name.lower())
                    pkg_download_tag_file = os.path.join(self._download_dir, '.' + name.lower() + '.tag')
                    with ZipFile(dest, 'r') as zipObj:
                        # Extract all the contents of zip file in different directory
                        zipObj.extractall(pkg_download_dir)
                    f = IniFile(pkg_download_tag_file)
                    f.set(None, 'url', url)
                    f.set(None, 'rev', site_rev)
                    f.save(pkg_download_tag_file)
                    f.close()
        return 0


    def _update_package_repo(self):
        mkdir_p(self._repo_dir)
        for name, details in package_list.items():
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
                repo_subdir = details.get('repo_subdir', '')
                pkg_download_tag_file = os.path.join(self._download_dir, '.' + name.lower() + '.tag')
                rev = None
                url = None
                if os.path.isfile(pkg_download_tag_file):
                    f = IniFile(pkg_download_tag_file)
                    rev = f.getAsInteger(None, 'rev', None)
                    url = f.get(None, 'url', None)
                    f.close()
                pkg_download_dir = os.path.join(self._download_dir, name.lower(), repo_subdir)
                if os.path.isdir(pkg_download_dir):
                    print('Update %s from %s' % (name.lower(), pkg_download_dir))
                    if copy_and_overwrite(pkg_download_dir, repo_dir):
                        if rev and url:
                            commit_msg = 'Automatic update from %s revision %i' % (url, rev)
                        else:
                            commit_msg = 'Automatic update'

                        debian_package_name = None
                        debian_package_version = None
                        debian_package_orig_version = None
                        debian_package_update_ok = False
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
                        except IOError:
                            pass

                        if setup_py_version:
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
                                debian_package_orig_version = setup_py_version + '+svn%i' % rev
                                new_version = debian_package_orig_version + '-'
                                if old_version.startswith(new_version):
                                    i = old_version.find('-')
                                    if i:
                                        new_version = new_version + '%i' % (int(old_version[i+1:]) + 1)
                                else:
                                    new_version = new_version + '1'

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
                            except IOError:
                                pass

                        if debian_package_update_ok:
                            if pkgrepo == 'git':
                                try:
                                    (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'commit', '-am', commit_msg], cwd=repo_dir)
                                except FileNotFoundError as ex:
                                    print('Cannot execute git.', file=sys.stderr)
                                    sts = -1

                                prefix = debian_package_name + '-' + debian_package_orig_version
                                pkgfile = os.path.join(repo_dir, '..', debian_package_name + '_' + debian_package_version + '.orig.tar.xz')
                                if not git_archive_xz(repo_dir, pkgfile, prefix):
                                    print('Failed to create %s.' % pkgfile, file=sys.stderr)
                    else:
                        print('Failed to copy to %s' % repo_dir, file=sys.stderr)
            else:
                print('Repository %s failed' % repo_dir, file=sys.stderr)


    def main(self):
        #=============================================================================================
        # process command line
        #=============================================================================================
        parser = argparse.ArgumentParser(description='update/generate trac packages')
        parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='enable verbose output of this script.')
        parser.add_argument('-l', '--list', dest='list', action='store_true', help='show list of all packages.')
        parser.add_argument('-d', '--download', dest='download', action='store_true', help='download the latest version of all packages.')
        parser.add_argument('-u', '--update', dest='update', action='store_true', help='update the package repositories.')

        args = parser.parse_args()
        self._verbose = args.verbose

        base_dir = os.path.abspath(os.getcwd())
        self._download_dir = os.path.join(base_dir, 'download')
        self._repo_dir = os.path.join(base_dir, 'repo')

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
        elif args.download:
            ret = self._download_pkgs()
        elif args.update:
            ret = self._update_package_repo()
        else:
            ret = 0

        return ret


if __name__ == "__main__":
    app =  trac_package_update_app()
    sys.exit(app.main())
