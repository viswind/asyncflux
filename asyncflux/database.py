# -*- coding: utf-8 -*-
"""Database level operations"""
from tornado import gen
from tornado.util import basestring_type

from asyncflux import retentionpolicy, user
from asyncflux.util import asyncflux_coroutine


class Database(object):

    def __init__(self, client, name):
        self.__client = client
        self.__name = name

    @property
    def client(self):
        return self.__client

    @property
    def name(self):
        return self.__name

    @asyncflux_coroutine
    def query(self, query, params=None, epoch=None, raise_errors=True):
        result_set = yield self.client.query(query, params, epoch,
                                             database=self.name,
                                             raise_errors=raise_errors)
        raise gen.Return(result_set)

    @asyncflux_coroutine
    def get_series(self):
        result_set = yield self.query('SHOW SERIES')
        series = []
        for serie in result_set[0].items():
            series.append({'name': serie[0][0],
                           'tags': list(serie[1])})
        raise gen.Return(series)

    @asyncflux_coroutine
    def drop_series(self, measurement=None, tags=None):
        query_list = ['DROP SERIES']
        if measurement:
            query_list.append('FROM "{}"'.format(measurement))
        if tags:
            tags_str = ' and '.join(["{}='{}'".format(k, v)
                                     for k, v in tags.items()])
            query_list.append('WHERE {}'.format(tags_str))
        yield self.query(' '.join(query_list))

    def __get_username(self, username_or_user):
        username = username_or_user
        if isinstance(username, user.User):
            username = username_or_user.name
        if not isinstance(username, basestring_type):
            raise TypeError("username_or_user must be an instance of "
                            "%s or User" % (basestring_type.__name__,))
        return username

    @asyncflux_coroutine
    def grant_privilege_to(self, privilege, username_or_user):
        username = self.__get_username(username_or_user)
        yield self.client.grant_privilege(privilege, username, self.name)

    @asyncflux_coroutine
    def revoke_privilege_from(self, privilege, username_or_user):
        username = self.__get_username(username_or_user)
        yield self.client.revoke_privilege(privilege, username, self.name)

    @asyncflux_coroutine
    def get_retention_policies(self):
        query_str = 'SHOW RETENTION POLICIES ON {}'.format(self.name)
        result_set = yield self.client.query(query_str)
        retention_policies = [
            retentionpolicy.RetentionPolicy(self, point['name'],
                                            point['duration'],
                                            point['replicaN'],
                                            point['default'])
            for point
            in result_set[0].get_points()
        ]
        raise gen.Return(retention_policies)

    @asyncflux_coroutine
    def get_retention_policy_names(self):
        query_str = 'SHOW RETENTION POLICIES ON {}'.format(self.name)
        result_set = yield self.client.query(query_str)
        retention_policies = [
            point['name']
            for point
            in result_set[0].get_points()
        ]
        raise gen.Return(retention_policies)

    @asyncflux_coroutine
    def create_retention_policy(self, retention_name, duration, replication,
                                default=False):
        query_format = ('CREATE RETENTION POLICY {} ON {} '
                        'DURATION {} REPLICATION {}')
        query_list = [
            query_format.format(retention_name, self.name, duration,
                                replication)
        ]
        if default:
            query_list.append('DEFAULT')
        yield self.client.query(' '.join(query_list))
        new_retention_policy = retentionpolicy.RetentionPolicy(self,
                                                               retention_name,
                                                               duration,
                                                               replication,
                                                               default)
        raise gen.Return(new_retention_policy)

    @asyncflux_coroutine
    def alter_retention_policy(self, retention_name, duration=None,
                               replication=None, default=False):
        query_list = ['ALTER RETENTION POLICY {} ON {}'.format(retention_name,
                                                               self.name)]
        if duration:
            query_list.append('DURATION {}'.format(duration))
        if replication:
            query_list.append('REPLICATION {}'.format(replication))
        if default:
            query_list.append('DEFAULT')
        yield self.client.query(' '.join(query_list))

    @asyncflux_coroutine
    def drop_retention_policy(self, retention_name):
        query_str = 'DROP RETENTION POLICY {} ON {}'.format(retention_name,
                                                            self.name)
        yield self.client.query(query_str)

    @asyncflux_coroutine
    def drop(self):
        yield self.client.drop_database(self.name)

    def __repr__(self):
        return "Database(%r, %r)" % (self.client, self.name)
