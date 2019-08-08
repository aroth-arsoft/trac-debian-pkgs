#!/usr/bin/python3
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;
import sys
import argparse
import urllib.request
import os
import os.path

package_list = {
    'AdvancedTicketWorkflowPlugin':  {
        'site': 'trac-hacks',
        'repo': 'svn',
        'repo_subdir': '1.2'
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
                filename = name.lower() + '.zip'
                dest = os.path.join(self._temp_dir, filename)
                print(url)
                urllib.request.urlretrieve(url, dest)
        return 0



    def main(self):
        #=============================================================================================
        # process command line
        #=============================================================================================
        parser = argparse.ArgumentParser(description='update/generate trac packages')
        parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='enable verbose output of this script.')
        parser.add_argument('-l', '--list', dest='list', action='store_true', help='show list of all packages.')
        parser.add_argument('-d', '--downlaod', dest='download', action='store_true', help='download the latest version of all packages.')

        args = parser.parse_args()
        self._verbose = args.verbose

        self._temp_dir = os.path.abspath(os.getcwd())

        if args.list:
            ret = self._list()
        elif args.download:
            ret = self._download_pkgs()
        else:
            ret = 0

        return ret


if __name__ == "__main__":
    app =  trac_package_update_app()
    sys.exit(app.main())
