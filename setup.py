#!/usr/bin/python3
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;
import sys
import argparse
import urllib.request
import errno
import shutil
import os
import os.path
from zipfile import ZipFile
from arsoft.utils import *

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

def copy_and_overwrite(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path)

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

    def _list(self):
        self._get_latest_revisions()
        for name, details in site_list.items():
            print('Site %s' % name)
            print('  Revision: %s' % details.get('revision'))
        for name, details in package_list.items():
            print('%s' % name)
            print('  URL: %s' % details.get('url'))
        return 0

    def _download_pkgs(self):
        self._get_latest_revisions()
        mkdir_p(self._download_dir)
        for name, details in package_list.items():
            print('%s' % name)
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
                    with ZipFile(dest, 'r') as zipObj:
                        # Extract all the contents of zip file in different directory
                        zipObj.extractall(pkg_download_dir)
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
                            (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'pull', 'origin'])
                        except FileNotFoundError as ex:
                            print('Cannot execute git.', file=sys.stderr)
                            sts = -1
                        print(stdoutdata, stderrdata)
                    else:
                        try:
                            (sts, stdoutdata, stderrdata) = runcmdAndGetData(args=['git', 'clone', pkgrepo_url, repo_dir])
                        except FileNotFoundError as ex:
                            print('Cannot execute git.', file=sys.stderr)
                            sts = -1
                        print(stdoutdata, stderrdata)
                    repo_ok = True if sts == 0 else False

            if repo_ok:
                print('Repository %s ok' % repo_dir)
                repo_subdir = details.get('repo_subdir', '')
                pkg_download_dir = os.path.join(self._download_dir, name.lower(), repo_subdir)
                if os.path.isdir(pkg_download_dir):
                    copy_and_overwrite(pkg_download_dir, repo_dir)
            else:
                print('Repository %s failed' % repo_dir)


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
