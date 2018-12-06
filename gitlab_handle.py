#!/usr/bin/env python

import sys
import logging
import argparse
import requests
from requests.packages.urllib3.exceptions import HTTPWarning

logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRIVATE_TOKEN = "**********"
GITLAB_API = "https://*****/api/v4"
PROJECT_GROUP = 1234

requests.packages.urllib3.disable_warnings(HTTPWarning)
# logging.basicConfig(format='%(asctime)s %(message)s')

def project_print(summary):
    # print "%(name)s\t\t\t\t | %(opened)s\t | %(merged)s\t | %(closed)s\t | %(all)s" % summary
    print "{name:>30} | {opened:>6} | {merged:>6} | {closed:>6} |{all:>6}".format(**summary)

class GitLabHandle(object):
    """
    Gitlab connection and operation class
    """
    def __init__(self, api, token, group='', logger=logger):
        self.api = api
        self.request = requests.Session()
        self.request.verify = False
        self.request.headers.update({"PRIVATE-TOKEN": token})
        self.group = group
        self.projects = []
        self.mrs = []
        self.project_mrs = {}
        self.project_sum = {}
        self.logger = logger

    def load(self, url, target):
        """
        Python generator, lazy lister/loader
        """
        self.logger.info("GET", url)
        try:
            while True:
                page = self.request.get(url)
                if not page.ok:
                    self.logger.error("{0}\t{1}\t{2}".format(url,
                    page.status_code, page.text))
                    break
                for item in page.json():
                    target.append(item)
                    yield item
                next_link = getattr(page, 'links', {}).get('next', None)
                if not (next_link and next_link['url']):
                    break
                url = next_link['url']
        except Exception as e:
            self.logger.error(url, e)
            raise

    def list_projects(self):
        url = "{0}{1}/projects".format(
            self.api,
            "/groups/{0}".format(self.group) if self.group else ""
        )
        for project in self.projects or self.load(url, self.projects):
            yield project

    def list_merge_requests(self, state='all'):
        url = "{0}/merge_requests?state=all".format(self.api)
        for mr in self.mrs or self.load(url, self.mrs):
            if state=='all' or mr['state']==state:
                yield mr

    def get_project_mr(self, project_id, state='all'):
        project_mr = []
        url = "{0}/projects/{1}/merge_requests?state=all".format(self.api, project_id)
        for mr in self.project_mrs.get(project_id, self.load(url, project_mr)):
            if state=='all' or mr['state']==state:
                yield mr
        if project_id not in self.project_mrs:
            self.project_mrs[project_id] = project_mr

    def get_project_summary(self, project):
        project_id = project['id']
        summary = {
            'id': project_id,
            'name': project['name'],
        }
        for state in ('all', 'opened', 'closed', 'locked', 'merged'):
            summary[state] = 0
        for mr in self.get_project_mr(project_id):
            summary['all'] += 1
            summary[mr['state']] += 1
        if project_id not in self.project_sum:
            self.project_sum[project_id] = summary
        return summary

    def print_project_summary(self, pprint=project_print):
        header = {'all': 'All', 'opened': 'Opened', 'closed':'Closed', 'id':'ID',
                  'locked': 'Locked', 'merged': 'Merged', 'name': 'Project Name'}
        pprint(header)
        for project in self.list_projects():
            pprint(
                self.project_sum.get(
                    project['id'],
                    self.get_project_summary(project)
                )
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a','--api', type=str,
        default=GITLAB_API, help='Gitlab API endpoint')
    parser.add_argument('-t','--token', type=str,
        default=PRIVATE_TOKEN, help='Gitlab API access token')
    parser.add_argument('-g','--group', type=str,
        default=PROJECT_GROUP, help='Gitlab project group id')
    args = parser.parse_args()

    glh = GitLabHandle(args.api, args.token, args.group)
    glh.print_project_summary()
